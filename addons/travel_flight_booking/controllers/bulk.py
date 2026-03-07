from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_path
import os


class FlightBulkController(http.Controller):
    @http.route('/travel_flight_booking/sample_download', type='http', auth='user')
    def sample_download(self, **kw):
        fmt = kw.get('format', 'xlsx')
        # prefer xlsx when requested and openpyxl is available
        try:
            this_file = os.path.abspath(__file__)
            module_dir = os.path.dirname(os.path.dirname(this_file))
            csv_path = os.path.join(module_dir, 'static', 'samples', 'flight_sample.csv')
        except Exception:
            return request.not_found()

        if fmt == 'xlsx':
            try:
                from io import BytesIO
                try:
                    # try openpyxl first
                    from openpyxl import Workbook
                    wb = Workbook()
                    ws = wb.active
                    with open(csv_path, 'r', encoding='utf-8') as f:
                        for r, line in enumerate(f):
                            # split by comma, preserve quoted fields
                            # simple CSV parse
                            if r == 0:
                                headers = next(csv.reader([line]))
                                ws.append(headers)
                            else:
                                row = next(csv.reader([line]))
                                ws.append(row)
                    bio = BytesIO()
                    wb.save(bio)
                    bio.seek(0)
                    data = bio.read()
                    headers = [
                        ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        ('Content-Disposition', 'attachment; filename="flight_sample.xlsx"'),
                    ]
                    return request.make_response(data, headers=headers)
                except Exception:
                    # fallback to csv if openpyxl not installed or fails
                    pass
            except Exception:
                pass

        # default: serve CSV
        try:
            with open(csv_path, 'rb') as f:
                data = f.read()
        except Exception:
            return request.not_found()
        headers = [
            ('Content-Type', 'text/csv; charset=utf-8'),
            ('Content-Disposition', 'attachment; filename="flight_sample.csv"'),
        ]
        return request.make_response(data, headers=headers)
