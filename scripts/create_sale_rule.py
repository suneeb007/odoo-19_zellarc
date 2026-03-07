#!/usr/bin/env python3
from odoo.modules.registry import Registry
from odoo import api
DB='zellarc_technologies'

def main():
    reg = Registry.new(DB)
    with reg.cursor() as cr:
        env = api.Environment(cr, 1, {})
        model = env['ir.model'].search([('model','=', 'sale.order')], limit=1)
        if not model:
            print('sale.order model not found')
            return
        domain = "['|',('message_ids.create_uid','=',user.id),('message_partner_ids','in',user.partner_id.id)]"
        vals = {
            'name': 'Lognote: read/write if author or mentioned',
            'model_id': model.id,
            'domain_force': domain,
            'perm_read': True,
            'perm_write': True,
            'perm_create': False,
            'perm_unlink': False,
            'global': False,
            'active': True,
        }
        rule = env['ir.rule'].search([('name','=', vals['name']),('model_id','=', model.id)], limit=1)
        if rule:
            rule.write(vals)
            print('updated rule')
        else:
            env['ir.rule'].create(vals)
            print('created rule')
        cr.commit()

if __name__ == '__main__':
    main()
