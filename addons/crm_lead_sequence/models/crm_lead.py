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

    _lead_number_unique = models.Constraint(
        'unique (lead_number)',
        'Lead number must be unique.',
    )

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
        
        # NOTE: do NOT auto-create flight.booking on create — creation is manual
        # via the `Flight OPS` button. Keep helper available in case it's needed.
        return records

    def write(self, vals):
        # Keep original value to detect changes
        res = super().write(vals)
        try:
            # Do NOT auto-create flight.booking on write. Creation is manual
            # through the `Flight OPS` button. Leaving hook for future use.
            pass
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
    
    def open_flight_ops(self):
        """Open a popup form to create a flight.booking with sensible defaults
        based on the lead. Returns an ir.actions.act_window dict."""
        self.ensure_one()
        partner = self.partner_id or self.env.user.partner_id
        # If a booking is already linked, open it
        if self.flight_booking_id:
            view = self.env.ref('travel_flight_booking.view_flight_booking_form', False)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'flight.booking',
                'res_id': self.flight_booking_id.id,
                'view_mode': 'form',
                'views': [(view.id, 'form')] if view else False,
                'target': 'current',
            }

        # Open an empty booking form in a popup with sensible defaults.
        # Do NOT create the record on button click; user must save to create.
        ctx = {
            'default_passenger_name': self.contact_name or self.name or (partner.name if partner else 'Passenger'),
            'default_client_id': partner.id if partner else False,
            'default_sectors': self.description or self.name or 'Unknown sector',
            'default_travel_date': fields.Date.context_today(self),
            'default_lead_id': self.id,
        }
        view = self.env.ref('travel_flight_booking.view_flight_booking_form', False)
        action = {
            'name': 'Flight Booking',
            'type': 'ir.actions.act_window',
            'res_model': 'flight.booking',
            'view_mode': 'form',
            'views': [(view.id, 'form')] if view else False,
            'target': 'new',
            'context': ctx,
        }
        return action

    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order', compute='_compute_sale_order_id', store=True,
        help='Most recent sale order linked to this opportunity')

    @api.depends('order_ids', 'order_ids.date_order', 'order_ids.state')
    def _compute_sale_order_id(self):
        for lead in self:
            orders = lead.order_ids.filtered(lambda o: o.state not in ('cancel',))
            if orders:
                # pick most recent by date_order if available, otherwise by id
                try:
                    orders = orders.sorted('date_order')
                    lead.sale_order_id = orders[-1]
                except Exception:
                    lead.sale_order_id = orders and orders[-1] or False
            else:
                lead.sale_order_id = False


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    lead_id = fields.Many2one('crm.lead', string='Lead')
    lead_number = fields.Char(string='Lead Number', readonly=True, store=True)

    @api.depends('lead_id', 'lead_id.lead_number', 'opportunity_id', 'opportunity_id.lead_number')
    def _compute_lead_number(self):
        for order in self:
            # Prefer explicit lead_id, fall back to opportunity_id (sale_crm flow)
            if order.lead_id and order.lead_id.lead_number:
                order.lead_number = order.lead_id.lead_number
            elif getattr(order, 'opportunity_id', False) and order.opportunity_id.lead_number:
                order.lead_number = order.opportunity_id.lead_number
            else:
                order.lead_number = False

    def action_confirm(self):
        """When a sale order is confirmed, mark the related lead/opportunity as won.

        This ensures opportunities converted to confirmed sales are closed as won.
        """
        res = super().action_confirm()
        Lead = self.env['crm.lead']
        leads_to_win = Lead.browse()
        for order in self:
            if order.lead_id:
                leads_to_win |= order.lead_id
            elif getattr(order, 'opportunity_id', False):
                leads_to_win |= order.opportunity_id
        if leads_to_win:
            try:
                leads_to_win.action_set_won()
            except Exception:
                _logger.exception('Failed to mark linked leads as won for sale orders: %s', self.ids)
        return res

    def action_cancel(self):
        """When a sale order is cancelled, move the linked lead/opportunity back
        to a non-won proposition stage and restore its probability.
        """
        res = super().action_cancel()
        Lead = self.env['crm.lead']
        leads_to_update = Lead.browse()
        for order in self:
            if order.lead_id:
                leads_to_update |= order.lead_id
            elif getattr(order, 'opportunity_id', False):
                leads_to_update |= order.opportunity_id
        for lead in leads_to_update:
            try:
                # Prefer a stage explicitly named 'Proposition' for the lead's team.
                # If not found, fall back to the first non-won stage.
                Stage = self.env['crm.stage']
                stage = False
                # Search globally for a 'Proposition' stage first.
                stage = Stage.search([('name', '=', 'Proposition')], limit=1)
                if not stage:
                    stage = lead._stage_find(team_id=lead.team_id.id, domain=[('is_won', '=', False)], limit=1)
                if stage:
                    # Only change the stage; do NOT modify probability per request.
                    lead.write({'stage_id': stage.id})
            except Exception:
                _logger.exception('Failed to move lead %s back to proposition on sale cancel', lead.id)
        return res
