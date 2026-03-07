from odoo import api, fields, models
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    lead_number = fields.Char(string='Lead Number', copy=False, readonly=True, index=True)
    service_type = fields.Selection([
        ('none', 'None'),
        ('air_ticket', 'Air Ticket'),
    ], string='Service', default='none')

    flight_booking_id = fields.Many2one('flight.booking', string='Flight Booking', copy=False)

    _sql_constraints = [
        ('lead_number_unique', 'unique(lead_number)', 'Lead number must be unique.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        date_str = datetime.now().strftime('%d%m%y')
        for vals in vals_list:
            if not vals.get('lead_number'):
                seq = self.env['ir.sequence'].next_by_code('crm.lead.ln') or '0'
                try:
                    seq_no = str(int(seq))
                except Exception:
                    seq_no = seq
                vals['lead_number'] = f'LN{date_str}{seq_no}'
        records = super().create(vals_list)
        # After create, if service is Air Ticket, try to create a flight.booking
        try:
            records.filtered(lambda r: r.service_type == 'air_ticket' and not r.flight_booking_id)._create_flight_booking_from_lead()
        except Exception:
            _logger.exception('Failed to auto-create flight.booking from lead')
        return records

    def write(self, vals):
        # Keep original value to detect changes
        res = super().write(vals)
        try:
            # For any leads updated to air_ticket, create booking if missing
            if 'service_type' in vals:
                self.filtered(lambda r: r.service_type == 'air_ticket' and not r.flight_booking_id)._create_flight_booking_from_lead()
        except Exception:
            _logger.exception('Failed to auto-create flight.booking from lead on write')
        return res

    def _create_flight_booking_from_lead(self):
        FlightBooking = self.env['flight.booking']
        Partner = self.env['res.partner']
        to_create = self.filtered(lambda r: not r.flight_booking_id)
        if not to_create:
            return
        # guard if travel module not installed
        module = self.env['ir.module.module'].sudo().search([('name', '=', 'travel_flight_booking'), ('state', '=', 'installed')], limit=1)
        if not module:
            _logger.warning('travel_flight_booking module not installed; skipping flight.booking creation')
            return
        vals_list = []
        for rec in to_create:
            partner = rec.partner_id or (Partner.search([('name', 'ilike', rec.partner_name or '')], limit=1) or self.env.user.partner_id)
            vals = {
                'passenger_name': rec.contact_name or rec.name or (partner.name if partner else 'Passenger'),
                'client_id': partner.id if partner else self.env.user.partner_id.id,
                'carrier_code': 'UNKNOWN',
                'airline_pnr': f'AUTO-{rec.lead_number or rec.id}',
                'pnr': rec.lead_number or rec.name,
                'sectors': rec.description or rec.name or 'Unknown sector',
                'travel_date': fields.Date.context_today(rec),
            }
            vals_list.append(vals)
        try:
            bookings = FlightBooking.create(vals_list)
            # link created bookings back to leads (one-to-one by order)
            for lead, booking in zip(to_create, bookings):
                try:
                    lead.flight_booking_id = booking.id
                except Exception:
                    _logger.exception('Failed to write flight_booking_id on lead %s', lead.id)
        except Exception:
            _logger.exception('Failed to create flight.booking records for leads')
