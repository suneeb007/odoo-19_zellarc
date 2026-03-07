from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class FlightBooking(models.Model):
    _name = "flight.booking"
    _description = "Flight Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('flight.booking') if self.env['ir.sequence'].sudo().search([('code','=', 'flight.booking')], limit=1) else '/')
    date_issue = fields.Date(string="Date of Issue", required=True, default=fields.Date.context_today)
    carrier_code = fields.Char(string="Carrier Code", required=True)
    ticket_no = fields.Char(string="Ticket No")
    # Legacy PNR (optional) and Airline-specific PNR (mandatory)
    pnr = fields.Char(string="PNR")
    airline_pnr = fields.Char(string="Airline PNR", required=True)
    sectors = fields.Text(string="Sectors", required=True)
    travel_date = fields.Date(string="Travel Date", required=True)
    # link to originating CRM lead (optional)
    lead_id = fields.Many2one('crm.lead', string='Lead', ondelete='set null')
    lead_number = fields.Char(string='Lead Number', compute='_compute_lead_number', readonly=True, store=True)

    @api.depends('lead_id')
    def _compute_lead_number(self):
        for rec in self:
            if rec.lead_id:
                rec.lead_number = getattr(rec.lead_id, 'lead_number', False)
            else:
                rec.lead_number = False

    @api.model
    def default_get(self, fields):
        res = super(FlightBooking, self).default_get(fields)
        # When opened from a lead (we pass default_lead_id in context), ensure PNR and carrier are blank
        if self.env.context.get('default_lead_id'):
            if 'airline_pnr' in res:
                res['airline_pnr'] = False
            if 'carrier_code' in res:
                res['carrier_code'] = False
        return res
    ticket_type = fields.Selection([
        ('lcc','LCC'), ('full','Full service'), ('group','Group Ticket'), ('labour','Labour fare'),
        ('ad','AD Ticket'), ('seaman','Seaman Fare')
    ], string="Ticket Type")
    fare_basis = fields.Char(string="Fare Basis")
    rbd = fields.Char(string="RBD")
    booking_class = fields.Selection([
        ('eco','Economy'), ('prem','Premium economy'), ('bus','Business'), ('first','First class')
    ], string="Class of booking")
    passenger_name = fields.Char(string="Passenger Name", required=True)
    client_id = fields.Many2one('res.partner', string="Client", required=True)

    supplier_id = fields.Many2one('res.partner', string="Supplier (Vendor)", domain="[('supplier_rank','>',0)]")

    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.company.currency_id)
    basic_fare = fields.Monetary(string="Basic Fare", currency_field='currency_id')
    # Tax breakdown fields
    yq_tax = fields.Monetary(string="YQ Tax", currency_field='currency_id', default=0.0)
    yr_tax = fields.Monetary(string="YR Tax", currency_field='currency_id', default=0.0)
    other_taxes = fields.Monetary(string="Other Taxes", currency_field='currency_id', default=0.0)
    # Total airline tax is computed as sum of YQ, YR and Other Taxes
    total_airline_tax = fields.Monetary(string="Total Airline Tax", compute='_compute_total_airline_tax', store=True, currency_field='currency_id')
    margin = fields.Monetary(string="Margin", currency_field='currency_id')
    airline_total = fields.Monetary(string="Airline Total", compute='_compute_airline_total', store=True, currency_field='currency_id')
    total_fare = fields.Monetary(string="Total Fare", compute='_compute_total_fare', store=True, currency_field='currency_id')

    ticketing_staff = fields.Many2one('res.users', string="Ticketing Staff", default=lambda self: self.env.user)
    booking_pcc = fields.Char(string="Booking Pcc")
    branch_code = fields.Char(string="Branch Code")

    # allow logging other users
    logged_user_ids = fields.Many2many('res.users', string='Logged Users')

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')

    # Commission lines
    customer_commission_line_ids = fields.One2many('flight.booking.customer.commission', 'booking_id', string='Customer Commissions')
    supplier_commission_line_ids = fields.One2many('flight.booking.supplier.commission', 'booking_id', string='Supplier Commissions')

    customer_commission_total = fields.Monetary(string='Customer Commission Total', compute='_compute_commission_totals', store=True, currency_field='currency_id')
    supplier_commission_total = fields.Monetary(string='Supplier Commission Total', compute='_compute_commission_totals', store=True, currency_field='currency_id')

    net_payable_to_supplier = fields.Monetary(string='Net Payable to Supplier', compute='_compute_net_amounts', store=True, currency_field='currency_id')
    net_receivable_from_customer = fields.Monetary(string='Net Receivable from Customer', compute='_compute_net_amounts', store=True, currency_field='currency_id')

    # Related records counts for header stats
    sale_count = fields.Integer(string='Sales Orders', compute='_compute_related_counts', store=True)
    purchase_count = fields.Integer(string='Purchase Orders', compute='_compute_related_counts', store=True)
    invoice_count = fields.Integer(string='Invoices', compute='_compute_related_counts', store=True)
    attachment_count = fields.Integer(string='Attachments', compute='_compute_related_counts', store=True)

    # UI status fields (stored for view/header rendering)
    sale_status = fields.Selection([
        ('pending', 'Pending'),
        ('created', 'Created'),
    ], string='Sale Status', compute='_compute_order_status', store=True)
    purchase_status = fields.Selection([
        ('pending', 'Pending'),
        ('created', 'Created'),
    ], string='Purchase Status', compute='_compute_order_status', store=True)

    has_sale_order = fields.Boolean(string='Has Sale Order', compute='_compute_has_orders', store=True)
    has_purchase_order = fields.Boolean(string='Has Purchase Order', compute='_compute_has_orders', store=True)

    @api.depends('basic_fare', 'total_airline_tax')
    def _compute_airline_total(self):
        for rec in self:
            rec.airline_total = (rec.basic_fare or 0.0) + (rec.total_airline_tax or 0.0)

    @api.depends('yq_tax', 'yr_tax', 'other_taxes')
    def _compute_total_airline_tax(self):
        for rec in self:
            rec.total_airline_tax = (rec.yq_tax or 0.0) + (rec.yr_tax or 0.0) + (rec.other_taxes or 0.0)

    @api.depends('airline_total', 'margin')
    def _compute_total_fare(self):
        for rec in self:
            rec.total_fare = (rec.airline_total or 0.0) + (rec.margin or 0.0)

    def action_create_sale_order(self):
        self.ensure_one()
        _logger.info('action_create_sale_order called for flight.booking id=%s', self.id)
        # Only allow creating a new sale order when none exists or the existing one is cancelled
        if self.sale_order_id and getattr(self.sale_order_id, 'state', False) != 'cancel':
            raise UserError(_('A Sale Order already exists for this booking. Cancel it before creating a new one.'))
        SaleOrder = self.env['sale.order']
        Product = self.env['product.product']
        uom_unit = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        # find or create product 'Air Tickets'
        product = Product.search([('name', '=', 'Air Tickets')], limit=1)
        if not product:
            product = Product.create({
                'name': 'Air Tickets',
                'type': 'service',
                'sale_ok': True,
                'invoice_policy': 'order',
                'list_price': 0.0,
            })
        # create product description
        desc_lines = [
            ('Carrier code: %s' % (self.carrier_code or '')),
            ('Ticket No: %s' % (self.ticket_no or '')),
            ('PNR: %s' % (self.airline_pnr or self.pnr or '')),
            ('Passenger: %s' % (self.passenger_name or '')),
            ('Travel date: %s' % (self.travel_date or '')),
        ]
        description = '\n'.join(desc_lines)
        # create sale order
        partner = self.client_id or self.env.user.partner_id
        # Determine pricelist safely: prefer partner's pricelist, then company website pricelist if present,
        # then any company-level pricelist attribute, otherwise leave unset.
        pricelist = False
        if partner and getattr(partner, 'property_product_pricelist', False):
            pricelist = partner.property_product_pricelist
        else:
            pricelist = getattr(self.env.company, 'website_pricelist_id', False) or getattr(self.env.company, 'property_product_pricelist', False) or False
        so_vals = {
            'partner_id': partner.id,
        }
        if pricelist:
            so_vals['pricelist_id'] = pricelist.id
        so = SaleOrder.create(so_vals)
        # Price should be the net receivable from customer (total fare minus customer commission).
        price_for_customer = (self.net_receivable_from_customer if getattr(self, 'net_receivable_from_customer', None) is not None else (self.total_fare or 0.0))
        line_vals = {
            'order_id': so.id,
            'product_id': product.id,
            'name': description,
            'product_uom_qty': 1.0,
            'product_uom_id': (product.uom_id.id if product.uom_id else (uom_unit.id if uom_unit else False)),
            'price_unit': price_for_customer,
        }
        # defensive: accept either legacy 'product_uom' or modern 'product_uom_id'
        if 'product_uom' in line_vals:
            line_vals['product_uom_id'] = line_vals.pop('product_uom')
        # Filter out any keys that are not fields of sale.order.line to avoid Invalid field errors
        SaleOrderLine = self.env['sale.order.line']
        allowed_fields = set(SaleOrderLine._fields.keys())
        filtered_vals = {k: v for k, v in line_vals.items() if k in allowed_fields}
        # use error-level logging to ensure visibility in all log configurations
        _logger.error('Creating sale.order.line (filtered vals): %s', filtered_vals)
        _logger.error('flight_booking: product %s, uom_id %s, original_has_product_uom=%s', product.id, filtered_vals.get('product_uom_id'), 'product_uom' in line_vals)
        try:
            so_line = SaleOrderLine.create([filtered_vals])
        except Exception:
            _logger.exception('Failed to create sale.order.line with vals: %s', filtered_vals)
            raise
        # Set flight booking reference on the sale order and confirm it
        try:
            # set booking reference to sale order client reference
            if self.name:
                so.write({'client_order_ref': self.name, 'flight_booking_id': self.id})
        except Exception:
            _logger.exception('Failed to write client_order_ref on sale.order id=%s', so.id)
        try:
            so.action_confirm()
        except Exception:
            _logger.exception('Failed to confirm sale.order id=%s', so.id)
        self.sale_order_id = so.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': so.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_send_email(self):
        self.ensure_one()
        composer = self.env['mail.compose.message'].with_context(
            default_model='flight.booking',
            default_res_id=self.id,
            default_use_template=False,
            default_composition_mode='comment',
        ).create({})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'res_id': composer.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_purchase_order(self):
        """Create a purchase.order for the supplier using net_payable_to_supplier as price."""
        self.ensure_one()
        _logger.info('action_create_purchase_order called for flight.booking id=%s', self.id)
        if not self.supplier_id:
            raise UserError(_('No supplier configured for this booking'))
        # Only allow one active purchase order unless the existing one is cancelled
        if self.purchase_order_id and getattr(self.purchase_order_id, 'state', False) != 'cancel':
            raise UserError(_('A Purchase Order already exists for this booking. Cancel it before creating a new one.'))
        PurchaseOrder = self.env['purchase.order']
        PurchaseLine = self.env['purchase.order.line']
        Product = self.env['product.product']
        uom_unit = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        # find or create product 'Air Tickets'
        product = Product.search([('name', '=', 'Air Tickets')], limit=1)
        if not product:
            product = Product.create({
                'name': 'Air Tickets',
                'type': 'service',
                'purchase_ok': True,
                'invoice_policy': 'order',
                'list_price': 0.0,
            })
        # description
        desc_lines = [
            ('Carrier code: %s' % (self.carrier_code or '')),
            ('Ticket No: %s' % (self.ticket_no or '')),
            ('PNR: %s' % (self.airline_pnr or self.pnr or '')),
            ('Passenger: %s' % (self.passenger_name or '')),
            ('Travel date: %s' % (self.travel_date or '')),
        ]
        description = '\n'.join(desc_lines)
        # create purchase order
        po_vals = {
            'partner_id': self.supplier_id.id,
            'origin': (self.name or False),
        }
        po = PurchaseOrder.create(po_vals)
        # determine price: net payable to supplier (airline_total - supplier commission)
        price_for_supplier = (self.net_payable_to_supplier if getattr(self, 'net_payable_to_supplier', None) is not None else (self.airline_total or 0.0))
        line_vals = {
            'order_id': po.id,
            'product_id': product.id,
            'name': description,
            'product_qty': 1.0,
            'product_uom': (product.uom_id.id if product.uom_id else (uom_unit.id if uom_unit else False)),
            'product_uom_id': (product.uom_id.id if product.uom_id else (uom_unit.id if uom_unit else False)),
            'price_unit': price_for_supplier,
        }
        # defensive: filter to allowed purchase.order.line fields
        allowed_fields = set(PurchaseLine._fields.keys())
        filtered_vals = {k: v for k, v in line_vals.items() if k in allowed_fields}
        _logger.error('Creating purchase.order.line (filtered vals): %s', filtered_vals)
        try:
            po_line = PurchaseLine.create([filtered_vals])
        except Exception:
            _logger.exception('Failed to create purchase.order.line with vals: %s', filtered_vals)
            raise
        try:
            # Confirm purchase order if applicable
            if hasattr(po, 'button_confirm'):
                po.button_confirm()
            elif hasattr(po, 'action_confirm'):
                po.action_confirm()
        except Exception:
            _logger.exception('Failed to confirm purchase.order id=%s', po.id)
        # link the PO to the booking
        try:
            # write back to booking and to the purchase order a link to this booking
            po.write({'flight_booking_id': self.id})
            self.purchase_order_id = po.id
        except Exception:
            _logger.exception('Failed to write purchase_order_id on booking id=%s', self.id)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.depends('sale_order_id', 'purchase_order_id', 'name')
    def _compute_related_counts(self):
        Sale = self.env['sale.order']
        Purchase = self.env['purchase.order']
        Invoice = self.env['account.move']
        Attachment = self.env['ir.attachment']
        for rec in self:
            rec.sale_count = Sale.search_count([('flight_booking_id', '=', rec.id)])
            rec.purchase_count = Purchase.search_count([('flight_booking_id', '=', rec.id)])
            domain_invoice = ['|', ('invoice_origin', 'ilike', rec.name or ''), ('invoice_line_ids.sale_line_ids.order_id.flight_booking_id', '=', rec.id)]
            rec.invoice_count = Invoice.search_count(domain_invoice)
            rec.attachment_count = Attachment.search_count([('res_model', '=', 'flight.booking'), ('res_id', '=', rec.id)])

    def action_open_sales(self):
        self.ensure_one()
        # Prefer using an existing sale action (provides proper view ids). Fallback to a safe form-only action.
        xml_ids = [
            'sale.action_orders',
            'sale.action_quotations_with_onboarding',
            'sale.action_quotations',
        ]
        for xml_id in xml_ids:
            try:
                action = self.env['ir.actions.actions']._for_xml_id(xml_id)
                action = self._ensure_action_has_views(action, 'sale.order')
                action['domain'] = [('flight_booking_id', '=', self.id)]
                action['context'] = dict(self.env.context)
                return action
            except Exception:
                continue
        # fallback: attempt to include explicit tree/form views if available
        views = []
        tree_view = self.env['ir.ui.view'].search([('model', '=', 'sale.order'), ('type', '=', 'tree')], limit=1)
        form_view = self.env['ir.ui.view'].search([('model', '=', 'sale.order'), ('type', '=', 'form')], limit=1)
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))
        action = {
            'name': 'Sales Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form' if views else 'form',
            'views': views,
            'domain': [('flight_booking_id', '=', self.id)],
            'context': {},
        }
        action = self._ensure_action_has_views(action, 'sale.order')
        _logger.error('action_open_sales returning action: %s', action)
        return action

    def action_open_purchases(self):
        self.ensure_one()
        xml_ids = [
            'purchase.purchase_rfq',
            'purchase.action_purchase_rfq',
            'purchase.purchase_action_purchases',
        ]
        for xml_id in xml_ids:
            try:
                action = self.env['ir.actions.actions']._for_xml_id(xml_id)
                action = self._ensure_action_has_views(action, 'purchase.order')
                action['domain'] = [('flight_booking_id', '=', self.id)]
                action['context'] = dict(self.env.context)
                return action
            except Exception:
                continue
        views = []
        tree_view = self.env['ir.ui.view'].search([('model', '=', 'purchase.order'), ('type', '=', 'tree')], limit=1)
        form_view = self.env['ir.ui.view'].search([('model', '=', 'purchase.order'), ('type', '=', 'form')], limit=1)
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))
        action = {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form' if views else 'form',
            'views': views,
            'domain': [('flight_booking_id', '=', self.id)],
            'context': {},
        }
        action = self._ensure_action_has_views(action, 'purchase.order')
        _logger.error('action_open_purchases returning action: %s', action)
        return action

    def action_open_invoices(self):
        self.ensure_one()
        domain_invoice = ['|', ('invoice_origin', 'ilike', self.name or ''), ('invoice_line_ids.sale_line_ids.order_id.flight_booking_id', '=', self.id)]
        xml_ids = [
            'account.action_move_out_invoice_type',
            'account.action_move_in_invoice_type',
            'account.action_move',
        ]
        for xml_id in xml_ids:
            try:
                action = self.env['ir.actions.actions']._for_xml_id(xml_id)
                action = self._ensure_action_has_views(action, 'account.move')
                action['domain'] = domain_invoice
                action['context'] = dict(self.env.context)
                return action
            except Exception:
                continue
        views = []
        tree_view = self.env['ir.ui.view'].search([('model', '=', 'account.move'), ('type', '=', 'tree')], limit=1)
        form_view = self.env['ir.ui.view'].search([('model', '=', 'account.move'), ('type', '=', 'form')], limit=1)
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))
        action = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form' if views else 'form',
            'views': views,
            'domain': domain_invoice,
            'context': {},
        }
        action = self._ensure_action_has_views(action, 'account.move')
        _logger.error('action_open_invoices returning action: %s', action)
        return action

    def action_open_attachments(self):
        self.ensure_one()
        xml_ids = [
            'base.action_attachment_tree',
        ]
        domain = [('res_model', '=', 'flight.booking'), ('res_id', '=', self.id)]
        for xml_id in xml_ids:
            try:
                action = self.env['ir.actions.actions']._for_xml_id(xml_id)
                action['domain'] = domain
                action['context'] = dict(self.env.context)
                return action
            except Exception:
                continue
        views = []
        tree_view = self.env['ir.ui.view'].search([('model', '=', 'ir.attachment'), ('type', '=', 'tree')], limit=1)
        form_view = self.env['ir.ui.view'].search([('model', '=', 'ir.attachment'), ('type', '=', 'form')], limit=1)
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))
        action = {
            'name': 'Attachments',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'tree,form' if views else 'form',
            'views': views,
            'domain': domain,
            'context': {},
        }
        action = self._ensure_action_has_views(action, 'ir.attachment')
        _logger.error('action_open_attachments returning action: %s', action)
        return action

    def _ensure_action_has_views(self, action, model):
        """Ensure an action dict includes view tuples matching its view_mode.

        If the action references view types (e.g. 'tree') but the 'views' array
        does not contain a matching view, search for a suitable view and append
        it. If no matching view exists, remove that type from `view_mode` and
        default to 'form'.
        """
        _logger.error('Ensuring action views for model %s: initial action %s', model, action)
        if not action or not isinstance(action, dict):
            _logger.error('_ensure_action_has_views: invalid action, returning as-is')
            return action
        views = action.get('views') or []
        normalized = []
        for item in views:
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    normalized.append((item[0], item[1]))
                elif isinstance(item, int):
                    v = self.env['ir.ui.view'].browse(item)
                    if v and v.exists():
                        normalized.append((v.id, v.type))
            except Exception:
                continue
        view_mode = (action.get('view_mode') or '')
        needed = [t.strip() for t in view_mode.split(',') if t.strip()]
        existing_types = {t for (_, t) in normalized}
        updated_needed = []
        for t in needed:
            if t in existing_types:
                updated_needed.append(t)
                continue
            # try to find a view of this type for the model
            v = self.env['ir.ui.view'].search([('model', '=', model), ('type', '=', t)], limit=1)
            if v:
                normalized.append((v.id, t))
                updated_needed.append(t)
            else:
                # no view of this type available -> skip it
                continue
        action['views'] = normalized
        action['view_mode'] = ','.join(updated_needed) if updated_needed else 'form'
        _logger.error('Ensured action for model %s: %s', model, action)
        return action

    @api.depends('customer_commission_line_ids.commission_amount', 'supplier_commission_line_ids.commission_amount')
    def _compute_commission_totals(self):
        for rec in self:
            rec.customer_commission_total = sum(line.commission_amount for line in rec.customer_commission_line_ids)
            rec.supplier_commission_total = sum(line.commission_amount for line in rec.supplier_commission_line_ids)

    @api.depends('sale_order_id', 'purchase_order_id')
    def _compute_order_status(self):
        for rec in self:
            rec.sale_status = 'created' if rec.sale_order_id and getattr(rec.sale_order_id, 'state', False) != 'cancel' else 'pending'
            rec.purchase_status = 'created' if rec.purchase_order_id and getattr(rec.purchase_order_id, 'state', False) != 'cancel' else 'pending'

    @api.depends('sale_order_id', 'purchase_order_id')
    def _compute_has_orders(self):
        for rec in self:
            rec.has_sale_order = bool(rec.sale_order_id and getattr(rec.sale_order_id, 'state', False) != 'cancel')
            rec.has_purchase_order = bool(rec.purchase_order_id and getattr(rec.purchase_order_id, 'state', False) != 'cancel')

    @api.depends('supplier_commission_total', 'customer_commission_total', 'airline_total', 'total_fare')
    def _compute_net_amounts(self):
        for rec in self:
            # Net payable to supplier = airline_total - supplier_commission_total
            rec.net_payable_to_supplier = (rec.airline_total or 0.0) - (rec.supplier_commission_total or 0.0)
            # Net receivable from customer = total_fare - customer_commission_total
            rec.net_receivable_from_customer = (rec.total_fare or 0.0) - (rec.customer_commission_total or 0.0)

    def action_log_users(self):
        for rec in self:
            if rec.logged_user_ids:
                names = ', '.join(rec.logged_user_ids.mapped('name'))
                rec.message_post(body=_('Logged users: %s') % names)

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        try:
            # Always generate a readable, unique booking reference FLT<DDMMYY><N>
            seq = self.env['ir.sequence'].next_by_code('flight.booking.number') or '1'
            today = fields.Date.context_today(self)
            if isinstance(today, str):
                # convert string to date
                import datetime
                today_date = datetime.datetime.strptime(today, '%Y-%m-%d').date()
            else:
                today_date = today
            ddmmyy = today_date.strftime('%d%m%y')
            new_name = f"FLT{ddmmyy}{seq}"
            rec.write({'name': new_name})
        except Exception:
            _logger.exception('Failed to generate flight booking reference for record id=%s', rec.id)
        return rec


class FlightBookingCommissionLineBase(models.AbstractModel):
    _name = 'flight.booking.commission.base'
    _description = 'Abstract base for commission lines'

    booking_id = fields.Many2one('flight.booking', string='Booking', ondelete='cascade')

    commission_type = fields.Selection([
        ('basic', 'On Basic Amount'),
        ('basic_yq', 'On Basic + YQ'),
        ('total', 'On Total Ticket Amount'),
    ], string='Commission Type', required=True, default='total')
    percentage = fields.Float(string='Percentage', digits='Account')
    base_amount = fields.Monetary(string='Base Amount', compute='_compute_base_amount', currency_field='currency_id')
    commission_amount = fields.Monetary(string='Commission Amount', compute='_compute_commission_amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='booking_id.currency_id', store=True, readonly=True)

    @api.depends('commission_type', 'percentage', 'booking_id.basic_fare', 'booking_id.yq_tax', 'booking_id.total_fare')
    def _compute_base_amount(self):
        for rec in self:
            if not rec.booking_id:
                rec.base_amount = 0.0
                continue
            if rec.commission_type == 'basic':
                rec.base_amount = rec.booking_id.basic_fare or 0.0
            elif rec.commission_type == 'basic_yq':
                rec.base_amount = (rec.booking_id.basic_fare or 0.0) + (rec.booking_id.yq_tax or 0.0)
            else:
                rec.base_amount = rec.booking_id.total_fare or 0.0

    @api.depends('base_amount', 'percentage')
    def _compute_commission_amount(self):
        for rec in self:
            rec.commission_amount = (rec.base_amount or 0.0) * (rec.percentage or 0.0) / 100.0


class FlightBookingCustomerCommission(models.Model):
    _name = 'flight.booking.customer.commission'
    _inherit = 'flight.booking.commission.base'
    _description = 'Customer Commission Line'

    # Explicitly declare fields here to ensure they are available to the view
    commission_type = fields.Selection([
        ('basic', 'On Basic Amount'),
        ('basic_yq', 'On Basic + YQ'),
        ('total', 'On Total Ticket Amount'),
    ], string='Commission Type', required=True, default='total')
    percentage = fields.Float(string='Percentage', digits='Account')



class FlightBookingSupplierCommission(models.Model):
    _name = 'flight.booking.supplier.commission'
    _inherit = 'flight.booking.commission.base'
    _description = 'Supplier Commission Line'

    # Explicitly declare fields here to ensure they are available to the view
    commission_type = fields.Selection([
        ('basic', 'On Basic Amount'),
        ('basic_yq', 'On Basic + YQ'),
        ('total', 'On Total Ticket Amount'),
    ], string='Commission Type', required=True, default='total')
    percentage = fields.Float(string='Percentage', digits='Account')


