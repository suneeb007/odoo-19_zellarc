from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import csv
import io
import traceback
from datetime import datetime


class FlightBookingBulkUpload(models.TransientModel):
    _name = 'flight.booking.bulk.upload'
    _description = 'Bulk upload Flight Bookings'

    file = fields.Binary('File')
    filename = fields.Char('File Name')

    def action_import(self):
        self.ensure_one()
        try:
            if not self.file:
                raise UserError(_('Please select a file to import'))
            data = base64.b64decode(self.file)
            try:
                s = data.decode('utf-8')
            except Exception:
                s = data.decode('latin-1')

            # detect delimiter
            sample = s[:8192]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '\t', '|'])
                delim = dialect.delimiter
            except Exception:
                delim = ','

            f = io.StringIO(s)
            csv_reader = csv.reader(f, delimiter=delim)
            try:
                header = next(csv_reader)
            except StopIteration:
                raise UserError(_('The file is empty'))
            headers = [h.strip().lower().replace(' ', '_').replace('*', '') for h in header]

            Flight = self.env['flight.booking']
            Partner = self.env['res.partner']
            created = []
            required_fields = ['date_issue', 'carrier_code', 'airline_pnr', 'sectors', 'travel_date', 'passenger_name', 'client_id', 'currency_id']
            row_no = 1
            errors = []

            for raw_row in csv_reader:
                # skip empty rows
                if not raw_row or all((not (c or '').strip()) for c in raw_row):
                    row_no += 1
                    continue
                row_no += 1
                # map normalized headers to values
                row = {headers[i]: (raw_row[i] if i < len(raw_row) else '') for i in range(len(headers))}

                try:
                    with self.env.cr.savepoint():
                        vals = {}
                        for key, raw_val in row.items():
                            val = (raw_val or '').strip()
                            if not val:
                                continue
                            key2 = key.strip().lower().replace(' ', '_').replace('*', '')
                            if key2 in ['client_id', 'supplier_id']:
                                name = val
                                partner = Partner.search([('name', '=', name)], limit=1)
                                if not partner:
                                    partner = Partner.create({'name': name})
                                vals[key2] = partner.id
                            elif key2 == 'currency_id':
                                code = val
                                currency = self.env['res.currency'].search([('name', '=', code)], limit=1)
                                if currency:
                                    vals['currency_id'] = currency.id
                            elif key2 in Flight._fields:
                                field = Flight._fields.get(key2)
                                if field.type == 'many2one':
                                    if val.isdigit():
                                        vals[key2] = int(val)
                                    else:
                                        comodel = field.comodel_name
                                        target = self.env[comodel]
                                        rec = None
                                        if comodel == 'res.users':
                                            rec = target.search([('login', '=', val)], limit=1)
                                            if not rec:
                                                rec = target.search([('name', '=', val)], limit=1)
                                        else:
                                            rec = target.search([('name', '=', val)], limit=1)
                                        if not rec:
                                            if comodel == 'res.partner':
                                                rec = target.create({'name': val})
                                            else:
                                                raise ValueError('unknown %s: %s' % (key2, val))
                                        vals[key2] = rec.id
                                elif field.type == 'integer':
                                    try:
                                        vals[key2] = int(val)
                                    except Exception:
                                        vals[key2] = val
                                elif field.type in ('float', 'monetary'):
                                    try:
                                        vals[key2] = float(val)
                                    except Exception:
                                        vals[key2] = val
                                elif field.type in ('date', 'datetime'):
                                    parsed = None
                                    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y'):
                                        try:
                                            dt = datetime.strptime(val, fmt)
                                            parsed = dt.date().isoformat()
                                            break
                                        except Exception:
                                            continue
                                    if parsed:
                                        vals[key2] = parsed
                                    else:
                                        vals[key2] = val
                                else:
                                    vals[key2] = val

                        missing = [f for f in required_fields if f not in vals or not vals.get(f)]
                        if missing:
                            errors.append('Row %s: missing %s' % (row_no, ','.join(missing)))
                            continue

                        rec = Flight.create(vals)
                        created.append(rec)

                        # Optionally create Sales Order
                        try:
                            create_so = (row.get('create_sales_order') or '').strip().lower() in ('1', 'yes', 'true')
                            sales_partner = (row.get('sales_partner') or '').strip()
                            if create_so or sales_partner:
                                so_partner_name = sales_partner or row.get('client_id')
                                if so_partner_name:
                                    so_partner = Partner.search([('name', '=', so_partner_name)], limit=1)
                                    if not so_partner:
                                        so_partner = Partner.create({'name': so_partner_name})
                                    so_vals = {
                                        'partner_id': so_partner.id,
                                        'origin': rec.name or False,
                                        'client_order_ref': row.get('sales_order_ref') or False,
                                    }
                                    try:
                                        self.env['sale.order'].create(so_vals)
                                    except Exception:
                                        # model may not be installed or creation failed
                                        raise ValueError('failed_create_sale_order')

                        except ValueError:
                            raise
                        except Exception:
                            # don't block the booking for non-critical order creation errors
                            pass

                        # Optionally create Purchase Order
                        try:
                            create_po = (row.get('create_purchase_order') or '').strip().lower() in ('1', 'yes', 'true')
                            purchase_partner = (row.get('purchase_partner') or row.get('supplier_id') or '').strip()
                            if create_po or purchase_partner:
                                po_partner_name = purchase_partner
                                if po_partner_name:
                                    po_partner = Partner.search([('name', '=', po_partner_name)], limit=1)
                                    if not po_partner:
                                        po_partner = Partner.create({'name': po_partner_name})
                                    po_vals = {
                                        'partner_id': po_partner.id,
                                        'origin': rec.name or False,
                                        'partner_ref': row.get('purchase_order_ref') or False,
                                    }
                                    try:
                                        self.env['purchase.order'].create(po_vals)
                                    except Exception:
                                        raise ValueError('failed_create_purchase_order')
                        except ValueError:
                            raise
                        except Exception:
                            pass
                except ValueError as ve:
                    errors.append('Row %s: %s' % (row_no, ve))
                    continue
                except Exception as e:
                    errors.append('Row %s: error: %s' % (row_no, e))
                    continue

            if errors:
                raise UserError(_('Import finished with errors:\n%s') % ('\n'.join(errors)))

            # If the model does not have a tree view registered, open the
            # created records in form view (first record) to avoid client
            # errors about missing view types.
            model_name = Flight._name
            tree_view = self.env['ir.ui.view'].search([('model', '=', model_name), ('type', '=', 'tree')], limit=1)
            if tree_view:
                # try to find a form view as well
                form_view = self.env['ir.ui.view'].search([('model', '=', model_name), ('type', '=', 'form')], limit=1)
                views = []
                if tree_view:
                    views.append((tree_view.id, 'tree'))
                if form_view:
                    views.append((form_view.id, 'form'))
                else:
                    views.append((False, 'form'))
                action = {
                    'type': 'ir.actions.act_window',
                    'res_model': model_name,
                    'view_mode': 'tree,form' if form_view else 'tree',
                    'views': views,
                    'domain': [('id', 'in', [r.id for r in created])],
                }
                if tree_view:
                    action['view_id'] = tree_view.id
                return action
            else:
                # If only one record created, open it directly in form view.
                if created:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': model_name,
                        'view_mode': 'form',
                        'res_id': created[0].id,
                        'views': [(False, 'form')],
                        'target': 'current',
                    }
                # Fallback: return a simple action that does nothing useful but avoids the error
                return {'type': 'ir.actions.client', 'tag': 'reload'}
        except UserError:
            raise
        except Exception as exc:
            tb = traceback.format_exc()
            raise UserError(_('Import failed: %s\n\n%s') % (str(exc), tb))

    def action_download_sample(self):
        # Return a URL action to download the sample file without validating the wizard
        return {
            'type': 'ir.actions.act_url',
            'url': '/travel_flight_booking/sample_download?format=xlsx',
            'target': 'new',
        }
