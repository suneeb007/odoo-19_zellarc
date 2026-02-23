from odoo import api, fields, models
import datetime


class LeadSequenceCounter(models.Model):
    _name = "lead.sequence.counter"
    _description = "Daily counter for lead numbers"

    date = fields.Date(required=True)
    last = fields.Integer(default=0)

    @api.model
    def next_for_date(self, date_str):
        # date_str expected 'YYYY-MM-DD'
        rec = self.search([('date', '=', date_str)], limit=1)
        if not rec:
            rec = self.create({'date': date_str, 'last': 1})
            return 1
        rec.last = rec.last + 1
        return rec.last


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    lead_number = fields.Char(string='Lead Number', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        # Normalize input: support single dict, list of dicts, or nested lists
        if not isinstance(vals_list, (list, tuple)):
            vals_list = [vals_list]
        # flatten one level if items are lists
        normalized = []
        for item in vals_list:
            if isinstance(item, (list, tuple)):
                normalized.extend(item)
            else:
                normalized.append(item)
        vals_list = normalized

        for vals in vals_list:
            if not isinstance(vals, dict):
                continue
            if not vals.get('lead_number'):
                # use a record (user) so context_today can access env.tz
                today = fields.Date.context_today(self.env.user)
                # ensure YYYY-MM-DD
                if isinstance(today, str):
                    today_str = today
                else:
                    today_str = today.strftime('%Y-%m-%d')
                # get next counter for today
                counter = self.env['lead.sequence.counter'].sudo().next_for_date(today_str)
                # format short date YYMMDD
                try:
                    d = datetime.datetime.strptime(today_str, '%Y-%m-%d')
                    date_part = d.strftime('%y%m%d')
                except Exception:
                    date_part = today_str.replace('-', '')[2:]
                vals['lead_number'] = f"LN{date_part}{counter}"
        return super(CrmLead, self).create(vals_list)
