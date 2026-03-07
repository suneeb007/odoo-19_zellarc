from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_path
import os
import base64


class FlightBulkJsonController(http.Controller):
    @http.route('/travel_flight_booking/sample_download_json', type='json', auth='user')
    def sample_download_json(self, format='xlsx'):
        try:
            this_file = os.path.abspath(__file__)
            module_dir = os.path.dirname(os.path.dirname(this_file))
            csv_path = os.path.join(module_dir, 'static', 'samples', 'flight_sample.csv')
        except Exception:
            return {'error': 'sample_not_found'}
        try:
            with open(csv_path, 'rb') as f:
                data = f.read()
        except Exception:
            return {'error': 'read_failed'}

        # If XLSX requested and openpyxl available, build XLSX bytes
        if format == 'xlsx':
            try:
                from io import BytesIO
                import csv as _csv
                from openpyxl import Workbook
                wb = Workbook()
                ws = wb.active
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = _csv.reader(f)
                    for row in reader:
                        ws.append(row)
                bio = BytesIO()
                wb.save(bio)
                bio.seek(0)
                data = bio.read()
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename = 'flight_sample.xlsx'
            except Exception:
                # fallback to csv
                mimetype = 'text/csv'
                filename = 'flight_sample.csv'
        else:
            mimetype = 'text/csv'
            filename = 'flight_sample.csv'

        return {
            'b64': base64.b64encode(data).decode('ascii'),
            'mimetype': mimetype,
            'filename': filename,
        }
