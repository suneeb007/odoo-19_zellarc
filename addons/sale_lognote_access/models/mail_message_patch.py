from odoo import models, api, _
import re


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        # Call super to create messages first
        messages = super(MailMessage, self).create(vals_list)

        # Pattern to find partner mentions rendered by chatter: data-oe-model="res.partner" data-oe-id="<id>"
        partner_pattern = re.compile(r'data-oe-model="res.partner"\s+data-oe-id="(\d+)"')

        for msg, vals in zip(messages, vals_list):
            try:
                model_name = vals.get('model') or msg.model
                res_id = vals.get('res_id') or msg.res_id
                body = vals.get('body') or msg.body or ''
                if not model_name or not res_id:
                    continue

                # find partner ids mentioned
                partner_ids = [int(p) for p in partner_pattern.findall(body)]
                if not partner_ids:
                    continue

                # Subscribe partners to the thread (adds them as followers)
                try:
                    record = self.env[model_name].browse(res_id)
                except Exception:
                    record = None
                if record and record.exists():
                    # message_subscribe accepts partner_ids list
                    record.message_subscribe(partner_ids=partner_ids)
                # Also add mentioned partners on the message itself if the
                # `partner_ids` field exists (some mail.message variants).
                try:
                    if hasattr(msg, 'partner_ids'):
                        # add partners to the message partners m2m
                        msg.write({'partner_ids': [(4, pid) for pid in partner_ids]})
                except Exception:
                    pass
            except Exception:
                # keep message creation resilient; don't block on follower logic
                pass

        return messages
