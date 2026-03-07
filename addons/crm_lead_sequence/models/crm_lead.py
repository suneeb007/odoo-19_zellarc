from odoo import api, fields, models
from datetime import datetime


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    lead_number = fields.Char(string='Lead Number', copy=False, readonly=True, index=True)

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
        return super().create(vals_list)
