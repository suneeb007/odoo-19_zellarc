from odoo.modules.registry import Registry
from odoo import api
DB='zellarc_technologies'
reg = Registry.new(DB)
processed=0
subscribed=0
with reg.cursor() as cr:
    env=api.Environment(cr,1,{})
    Mail=env['mail.message']
    msgs=Mail.search([('body','ilike','data-oe-model="res.partner"')])
    print('found',len(msgs))
    for m in msgs:
        try:
            body=(m.body or '')
            if 'data-oe-model="res.partner"' not in body:
                continue
            ids=[]
            i=0
            while True:
                i=body.find('data-oe-id="',i)
                if i==-1:
                    break
                i+=len('data-oe-id="')
                j=i
                num=''
                while j<len(body) and body[j].isdigit():
                    num+=body[j]; j+=1
                if num:
                    ids.append(int(num))
                i=j
            if not ids:
                continue
            if m.model and m.res_id:
                try:
                    rec=env[m.model].browse(m.res_id)
                    if rec.exists():
                        rec.message_subscribe(partner_ids=ids)
                        subscribed+=1
                except Exception:
                    pass
            try:
                if hasattr(m,'partner_ids'):
                    m.write({'partner_ids': [(4,p) for p in ids]})
            except Exception:
                pass
            processed+=1
        except Exception as e:
            print('err',m.id,e)
print('done',processed,subscribed)
