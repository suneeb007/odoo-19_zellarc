from odoo import http
from odoo.http import request


class TravelHomeRedirect(http.Controller):
    @http.route('/', type='http', auth='public', website=True)
    def root_redirect(self, **kw):
        # Redirect anonymous and logged-in users to the Odoo home (apps/menu) page
        return request.redirect('/odoo')
