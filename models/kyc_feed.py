import logging
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..ai_msg_clasification.msg_classification import process_message

REQUIRED_KYC_FIELDS = ["customer_type", "products_list", "name", "company_name", "email", "isd_code", "phone", "address", "city", "state", "country", "website_link"]
ADDITIONAL_KYC_FIELDS = ["continent", "customer_language", "country_language"]
EXTRA_PRODUCT_DETAIL_FIELDS = ["loading_port", "monthly_quantity", "current_quantity", "loading_weight", "target_price", 'forms']

STATE = [
    ('draft', 'Grey List'),
    ('done', 'White List'),
    ('error', 'Red List')
]

class Feed(models.Model):
    _name = "kyc.feed"
    _inherit = ['mail.thread']
    _description = "KYC Feed Informations With Message History"

    name = fields.Char(string="Customer Name")
    company_name = fields.Char(string="Company Name")
    email = fields.Char(string="Email")
    isd_code = fields.Char(string="ISD Code")
    phone = fields.Char(string="Contact No.")
    address = fields.Char(string="Company Address")
    state = fields.Char(string="State")
    city = fields.Char(string="City")
    country = fields.Char(string="Country")
    website_link = fields.Char(string="Website Link")
    customer_type = fields.Selection(string='Customer Type',selection=[('buyer', 'Buyer'), ('seller', 'Seller')])
    kyc_state = fields.Selection(STATE, default='draft')
    lead_name = fields.Char(string='Lead Name')
    continent = fields.Char(string="Continent")
    customer_language = fields.Char(string="Customer Language")
    country_language = fields.Char(string="Country Language")
    
    # Business related fields
    loading_port = fields.Char(string="POL/POD")
    monthly_quantity = fields.Char(string="Monthly Quantity")
    current_quantity = fields.Char(string="Current quantity")
    loading_weight = fields.Char(string="Loading weight", help="Loading weight in each container")
    target_price = fields.Char(string="Target Price", help="Target price")
    fob_price = fields.Char(string="FOB Price", help="FOB price")

    # Product related information fields
    category = fields.Char(string="Categroy")
    forms = fields.Char(string="Forms")
    
    channel_id = fields.Many2one(
        string='Channel',
        comodel_name='multi.channel.crm',
    )
    
    
    is_kyc_complete = fields.Boolean(
        string='is_kyc_complete',
        compute='_compute_is_kyc_complete',
        store=True,
    )

    products_list = fields.Char(
        string="Product List"
    )

    identification_code = fields.Char(
        string='Identification Code',
        required=True,
        index=True,
    )
    
    msg_contents_history = fields.Json(
        string="WhatsApp Msg Content"
    )
    
    user_msg_count = fields.Integer(
        string='user_msg_count',
        default=0,
    )
    
    _sql_constraints = [
        (
            'unique_identification_code',
            'unique (identification_code)',
            _('The Identification Code already exists.')
        )
    ]

    @api.depends("name", "company_name", "email", "isd_code", "phone", "address", "city", "state", "country", "website_link", "customer_type", "products_list")
    def _compute_is_kyc_complete(self):
        for record in self:
            if (
                record.name
                and record.company_name
                and record.email
                and record.isd_code
                and record.phone
                and record.city
                and record.state
                and record.country
                and record.customer_type
                and record.products_list
            ):
                customer_type = dict(record._fields['customer_type'].selection).get(record.customer_type)
                record.write({
                    "is_kyc_complete": True,
                    "lead_name": record.products_list + " / " + customer_type,
                })
            else:
                record.is_kyc_complete = False

    def update_kyc_feed(self, response, msg=False, **args):
        try:
            response_msg = response.get("message_response", "")

            if not response_msg:
                return process_message(msg, **args)

            personal_information = response.get("customer_details", {})
            product_details = response.get("product_details", {})
            odoobot = self.env.ref('base.partner_root')
            values = {
                "user_msg_count": self.user_msg_count + 1
            }

            if not self.products_list and response.get("products_list", []):
                values["products_list"] = response.get("products_list")

            if not self.customer_type and response.get("customer_type", False):
                values["customer_type"] = response.get("customer_type")

            for field in REQUIRED_KYC_FIELDS[2::]:
                if not self[field] and personal_information.get(field, False):
                    values[field] = personal_information.get(field)

            for field in ADDITIONAL_KYC_FIELDS:
                if not self[field] and personal_information.get(field, False):
                    values[field] = personal_information.get(field)

            for field in EXTRA_PRODUCT_DETAIL_FIELDS:
                if not self[field] and product_details.get(field, False):
                    values[field] = product_details.get(field)                    

            self.message_post(body=Markup(f"<pre>{msg}</pre>"))
            self.message_post(body=Markup(f"<pre>{response_msg}</pre>"), author_id=odoobot.id)
            values["msg_contents_history"] = self.update_msg_history(msg, response_msg)
            self.write(values)
            
            if self.user_msg_count + 1 > 4 and not self.is_kyc_complete:
                self.kyc_state = "error"

            if self.is_kyc_complete and self.channel_id.auto_evaluate:
                self.feed_evaluate()
            
            return response_msg
        except Exception as e:
            logging.error(f"Updaing kyc feed failed: {e}")
            return "Failed to process your Information. \nWe will get back to you soon."

    def update_msg_history(self, msg, response_msg):
        content_list = self.msg_contents_history or []

        content_list += [
            {"user": msg},
            {"model": response_msg},
        ]

        return content_list

    def feed_evaluate(self):
        contact_mapping = self.env['channel.contact.mapping']
        lead_mapping = self.env['channel.lead.mapping']
        for rec in self:
            partner = rec.match_partner()
            if not partner:
                partner_vals = {
                    'name':rec.name,
                    'email':rec.email,
                    'website':rec.website_link,
                    'phone':rec.isd_code + rec.phone,
                    'crm_phone':rec.phone,
                    'company_name': rec.company_name,
                    'street':rec.address,
                    'city':rec.city,
                    'country_id':self.get_odoo_country(rec.country),
                    'state_id':self.get_odoo_state(rec.state)
                }
                partner = self.env['res.partner'].create(partner_vals)
                contact_mapping.create({'partner_id':partner.id, 'store_partner_id':partner.company_name, 'channel_id':rec.channel_id.id})
            if not (rec.lead_name or partner):
                rec.kyc_state = 'error'
                return False
            lead_vals = {
                    'name':rec.lead_name,
                    'partner_id':partner.id,
                    'customer_type':rec.customer_type,
                    'channel_id':rec.channel_id.id,
                    'monthly_quantity':rec.monthly_quantity,
                    'current_quantity':rec.current_quantity,
                    'target_price':rec.target_price,
                    'fob_price':rec.fob_price,
                    'loading_port':rec.loading_port,
                    'loading_weight':rec.loading_weight,
                }

            products_list = self.get_product(rec.products_list, rec.category, rec.forms)
            if not products_list:
                rec.kyc_state = 'error'
                return False

            lead_vals.update({'product_ids':products_list})
            lead = self.env['crm.lead'].create(lead_vals)
            lead_mapping.create({'lead_id':lead.id, 'lead_name':lead.name, 'channel_id':rec.channel_id.id})
            # Update The Kyc State:
            if not rec.kyc_state == 'done':
                rec.kyc_state = 'done'

    def get_product(self, products, category, form):
        product_ids = []
        if not products:
            return product_ids
        products = list(map(str.strip, products.split(",")))
        product_obj = self.env['product.template']
        for product in products:
            domain = ["|", ("name", "ilike", product), ("default_code", "ilike", product)]
            if form:
                domain.append(("forms_id.name", "ilike", form))
            match = product_obj.search(domain, limit=1)

            if not match:
                # GET DOMAIN VALUE FROM AI WITH DFFERENT VALUES e.g., ['P1','P2',....]
                AI_VALUES = self.get_ai_product_different_values()
                domain = ["|", ("name", "in", AI_VALUES), ("default_code", "in", AI_VALUES)]
                match = product_obj.search(domain, limit=1)

            if not match:
                return []
            product_ids.append(match.id)
        return product_ids
             

    def match_partner(self):
        # CHECK CUSTOMER MAPPING
        contact_mapping = self.env['channel.contact.mapping']
        domain = [("store_partner_id", "ilike", self.company_name)]
        match = contact_mapping.search(domain, limit=1)
        if not match:
            # CHECK ODOO CUSTOMER
            res_partner = self.env['res.partner']
            domain = [
                "|", "|", 
                ("company_name", "ilike", self.company_name), 
                ("email", "=", self.email), 
                ("crm_phone", "=", self.phone), 
            ]
            if self.website_link:
                domain = ["|"] + domain.append(("website", "ilike", self.website_link))
            match = res_partner.search(domain, limit=1)
        return match
            
    def get_ai_product_different_values(self):
        return []

    def get_odoo_country(self, country):
        country_id = self.env['res.country'].search([('name','ilike',country)], limit=1)
        return country_id.id if country_id else False

    def get_odoo_state(self, state):
        state_id = self.env['res.country.state'].search([('name','ilike',state)], limit=1)
        return state_id.id if state_id else False

    def open_mapping_view(self):
        self.ensure_one()
        model = self._context.get('mapping_model')
        action = {
            'name': 'Mapping',
            'type': 'ir.actions.act_window',
            'res_model': model,
            'target': 'current',
        }
        store_id = self.email
        if self._context.get('store_field') == 'lead_name':
            store_id = self.lead_name
        res = self.env[model].search(
            [
                ('channel_id', '=', self.channel_id.id),
                (self._context.get('store_field'), '=', store_id),
            ]
        )
        action.update(view_mode='form', res_id=res.id) if len(res) == 1 else action.update(view_mode='tree', domain=[('id', 'in', res.ids)])
        return action
