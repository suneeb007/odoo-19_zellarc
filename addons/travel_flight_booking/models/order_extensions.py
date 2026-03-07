from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    flight_booking_id = fields.Many2one('flight.booking', string='Flight Booking')

    def action_open_flight_booking(self):
        self.ensure_one()
        if not self.flight_booking_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'flight.booking',
            'res_id': self.flight_booking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    flight_booking_id = fields.Many2one('flight.booking', string='Flight Booking')

    def action_open_flight_booking(self):
        self.ensure_one()
        if not self.flight_booking_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'flight.booking',
            'res_id': self.flight_booking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
