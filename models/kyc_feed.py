import logging
_logger = logging.getLogger(__name__)

import json
from markupsafe import Markup
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


from ..ai_msg_clasification.msg_classification import process_message
from ..ai_msg_clasification.small_ai_queries import process_query

REQUIRED_KYC_FIELDS = ["customer_type", "name", "company_name", "email", "isd_code", "phone", "address", "city", "state", "country", "website_link"]
ADDITIONAL_KYC_FIELDS = ["continent", "customer_language", "country_language"]

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
    
    channel_id = fields.Many2one(
        string='Channel',
        comodel_name='multi.channel.crm',
    )
    
    is_kyc_complete = fields.Boolean(
        string='is_kyc_complete',
        compute='_compute_is_kyc_complete',
        store=True,
    )

    identification_code = fields.Char(
        string='Identification Code',
        required=True,
        index=True,
    )
    
    user_msg_count = fields.Integer(
        string='user_msg_count',
        default=0,
    )
    
    business_info_ids = fields.One2many(
        string='Business Information',
        comodel_name='business.information',
        inverse_name='kyc_feed_id',
    )
    
    is_ready_for_lead_creation = fields.Boolean(
        string='is_ready_for_lead_creation',
        compute='_compute_is_ready_for_lead_creation'
    )

    remark = fields.Html(string='Remark', default="")
        
        
    @api.depends('is_kyc_complete', 'business_info_ids')
    def _compute_is_ready_for_lead_creation(self):
        for record in self:
            # Add all the conditions to got_required_business_info
            got_required_business_info = True
            record.is_ready_for_lead_creation = record.is_kyc_complete and got_required_business_info
    
    _sql_constraints = [
        (
            'unique_identification_code',
            'unique (identification_code)',
            _('The Identification Code already exists.')
        )
    ]

    @api.depends("name", "company_name", "email", "isd_code", "phone", "address", "city", "state", "country", "website_link", "customer_type", "business_info_ids")
    def _compute_is_kyc_complete(self):
        for record in self:
            record.is_kyc_complete = False
            business_info_ids = record.business_info_ids
            if (
                record.name
                and record.company_name
                and record.email
                and record.phone
                and record.country
                and record.customer_type
                and business_info_ids
            ):

                if record.customer_type == 'buyer':
                    valid_lines = business_info_ids.filtered(
                        lambda l: l.loading_port
                    )
                elif record.customer_type == 'seller':
                    valid_lines = business_info_ids.filtered(
                        lambda l: l.loading_port and l.loading_weight and l.current_quantity
                        )
                else:
                    valid_lines = business_info_ids.browse([])

                if len(valid_lines) == len(business_info_ids):

                    # Check For Product Exist In Odoo:
                    is_products_exist = self.is_products_exist(business_info_ids)
                    if is_products_exist:
                        record.is_kyc_complete = True
                        customer_type_label = dict(record._fields['customer_type'].selection).get(record.customer_type)
                        product_names = ", ".join(valid_lines.mapped("product"))
                        record.lead_name = product_names + " / " + customer_type_label

    def is_products_exist(self, business_info_ids):
        Product = self.env["product.template"]
        remarks = []
        success = True

        for line in business_info_ids:
            domain = []

            # Start with product name / code
            if line.product:
                domain = ["|", ("name", "=", line.product), ("default_code", "=", line.product)]

            # Add forms if present
            if line.forms:
                domain = ["&"] + domain + [("forms_id.name", "ilike", line.forms)]

            # Add category filters if present
            if line.sub_category:
                domain = ["|"] + domain + [("sub_categ_id.name", "ilike", line.sub_category)]
            if line.child_category:
                domain = ["|"] + domain + [("child_categ_id.name", "ilike", line.child_category)]

            # Search product
            match = Product.search(domain, limit=1)

            # If not found, try AI synonyms
            if not match and line.product:
                query, SI = self.get_query_to_fetch_alternate_products_names(line.product)
                AI_VALUES = process_query(self.env, query, SI)
                domain = ["|", ("name", "in", AI_VALUES), ("default_code", "in", AI_VALUES)]
                if line.forms:
                    domain = ["&"] + domain + [("forms_id.name", "ilike", line.forms)]
                match = Product.search(domain, limit=1)

            if match:
                line.product_id = match.id  # link business.info → product
            else:
                remarks.append(f"Product not found: {line.product or 'N/A'}")
                success = False

        if not success:
            self.remark = "<br/>".join(remarks)

        return success


    def update_kyc_feed(self, response, msg=False, **args):
        try:
            response_msg = response.get("message_response", "")

            if not response_msg:
                limit = args.pop("limit") + 1
                return process_message(self.env, msg, limit=limit, **args)

            personal_information = response.get("customer_details", {})
            product_details = response.get("product_details", [])
            odoobot = self.env.ref('base.partner_root')
            values = {
                "user_msg_count": self.user_msg_count + 1
            }

            if not self.customer_type and response.get("customer_type", False):
                values["customer_type"] = response.get("customer_type")

            for field in REQUIRED_KYC_FIELDS[1::]:
                if not self[field] and personal_information.get(field, False):
                    values[field] = personal_information.get(field)

            for field in ADDITIONAL_KYC_FIELDS:
                if not self[field] and personal_information.get(field, False):
                    values[field] = personal_information.get(field)

            self.business_info_ids.unlink()

            values["business_info_ids"] = [Command.create(vals) for vals in product_details]

            user = self.env.ref("base.user_admin").partner_id
            self.message_post(body=Markup(f"<pre>{msg}</pre>"), author_id=user.id)
            self.message_post(body=Markup(f"<pre>{response_msg}</pre>"), author_id=odoobot.id)
            self.write(values)
            
            if self.channel_id.user_message_count_attempt and self.user_msg_count + 1 > self.channel_id.user_message_count_attempt and not self.is_kyc_complete:
                self.kyc_state = "error"

            if self.is_kyc_complete and self.channel_id.auto_evaluate:
                self.feed_evaluate()
            
            return response_msg
        except Exception as e:
            logging.error(f"Updaing kyc feed failed: {e}", exc_info=True)
            return "Failed to process your Information. \nWe will get back to you soon."

    def _retrieve_chat_history(self, no_messages=20):
        result = self.retrieve_chat_history()
        # odooBootId = self.env.ref('base.partner_root')
        # chat_history = [
        #     {
        #         'role': 'assistant' if message.author_id.id == odooBootId.id else 'user',
        #         'content': html2plaintext(message.body or '')
        #     }
        #     for message in self.message_ids[:no_messages]
        # ]

        return f"##Context information:\n\n{result}"

    def retrieve_chat_history(self):
        self.ensure_one()  # Optional: use only if called on a single record
        result = []
        for rec in self:
            customer_details = {
                "name": rec.name,
                "company_name": rec.company_name,
                "email": rec.email,
                "isd_code": rec.isd_code,
                "phone": rec.phone,
                "address": rec.address,
                "city": rec.city,
                "state": rec.state,
                "country": rec.country,
                "website_link": rec.website_link,
                "customer_language": rec.customer_language,
                "continent": rec.continent,
                "country_language": rec.country_language,
            }
            product_details = [{
                "product": info.product,
                "loading_port": info.loading_port,
                "monthly_quantity": info.monthly_quantity,
                "current_quantity": info.current_quantity,
                "loading_weight": info.loading_weight,
                "target_price": info.target_price,
                "fob_price": info.fob_price,
                "category": info.category,
                "forms": info.forms,
            } for info in rec.business_info_ids]
            result.append({
                "customer_type": rec.customer_type,
                "customer_details": customer_details,
                "product_details": product_details,
            })
        return result

    def feed_evaluate(self):
        contact_mapping = self.env['channel.contact.mapping']
        lead_mapping = self.env['channel.lead.mapping']
        message = ""
        for rec in self:
            if not rec.lead_name:
                message += "## Lead Name Missing"
                raise UserError("Lead Name Missing")

            partner = self.env['res.partner']
            match = rec.match_partner()
            if match:
                partner = match
            _logger.info("Partner Matched :",partner)
            if not partner:
                partner_vals = {
                    'name':rec.name,
                    'email':rec.email,
                    'website':rec.website_link,
                    'phone':rec.isd_code + rec.phone if rec.isd_code and rec.phone else rec.phone,
                    'crm_phone':rec.phone,
                    'company_name': rec.company_name,
                    'street':rec.address,
                    'city':rec.city,
                    'country_id':self.get_odoo_country(rec.country),
                    'state_id':self.get_odoo_state(rec.state),
                    'stop_conversation': True,
                }
                partner = self.env['res.partner'].create(partner_vals)
                contact_mapping.create({'partner_id':partner.id, 'store_partner_id':partner.company_name, 'channel_id':rec.channel_id.id})
            if not partner:
                message += "<br/>## No Partner Found"
                return UserError("No Partner Found")
            lead_vals = {
                    'name':rec.lead_name,
                    'partner_id':partner.id,
                    'customer_type':rec.customer_type,
                    'channel_id':rec.channel_id.id,
                    'continent':rec.continent,
                }
            if message:
                rec.remark = message

            products = rec.business_info_ids.mapped('product_id')

            products_list = self.get_product(products)

            if not products_list:
                return False

            for user_id, prod_ids in products_list.items():
                lead_data = lead_vals.copy()
                lead_data.update({
                    'user_id': user_id,
                    'product_ids': prod_ids,
                })

                lead = self.env['crm.lead'].create(lead_data)
                matched_lines = rec.business_info_ids.filtered(lambda line: line.product_id.id in prod_ids)
                matched_lines.write({'lead_id': lead.id})

                if rec.customer_type == 'seller':
                    supplier_code = lead.generate_supplier_code()
                    if supplier_code:
                        lead.generate_offer_codes()
                else:
                    offers_data = lead.get_matching_seller_offers()
                    if offers_data:
                        email_content = lead.prepare_offer_email_for_buyer(offers_data)
                        body = lead._build_html_offer_email(offers_data)
                        lead.message_post(
                            body=body,
                            subject=email_content['subject'],
                            message_type='email',
                            subtype_id=self.env.ref('mail.mt_comment').id,
                            partner_ids=[lead.partner_id.id] if lead.partner_id else [],
                            email_from=self.env.user.email,
                            )

                lead_mapping.create({
                    'lead_id': lead.id,
                    'lead_name': lead.name,
                    'channel_id': rec.channel_id.id
                })
            # Update The Kyc State:
            if not rec.kyc_state == 'done':
                rec.kyc_state = 'done'

    def get_product(self, products):
        product_ids = {}
        if not (products):
            return product_ids
        for product in products:
            user_id = product.crm_categ_id.user_id.id
            if not user_id:
                continue

            if user_id not in product_ids:
                product_ids[user_id] = [product.id]
            else:
                product_ids[user_id].append(product.id)

        return product_ids

    def match_partner(self):
        contact_mapping = self.env['channel.contact.mapping']
        partner_model = self.env['res.partner']

        # Step 1: Check in channel.contact.mapping
        if self.company_name:
            match = contact_mapping.search([("store_partner_id", "ilike", self.company_name)], limit=1)
            if match:
                return match.partner_id

        # Step 2: Check in res.partner with multiple fallback fields
        domain_parts = []
        if self.company_name:
            domain_parts.append(("company_name", "ilike", self.company_name))
        if self.email:
            domain_parts.append(("email", "=", self.email))
        if self.phone:
            domain_parts.append(("crm_phone", "=", self.phone))
        if self.website_link:
            domain_parts.append(("website", "ilike", self.website_link))

        if domain_parts:
            # Build stacked "|" domain (binary tree style)
            if len(domain_parts) == 1:
                domain = domain_parts
            else:
                domain = []
                for i in range(len(domain_parts) - 1):
                    domain.append("|")
                domain += domain_parts
            return partner_model.search(domain, limit=1)
        return False  # No input fields to match on


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
        store_id = self.company_name
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

    def get_query_to_fetch_alternate_products_names(self, product_name):
        INSTRUCTION = f"""
        Your task is to generate a list of different names and aliases for a specified {product_name}.
        Please provide the output in a list of strings.
        E.g.,
                    [
            "hdpe",
            "HDPE",
            "regrind",
            "REGRIND",
            "hdpe regrind",
            "HDPE REGRIND",
            "Hdpe Regrind",
            "HDPE RG",
            "hdpe rg"
            ]
        Guidelines:
            1. Include all common variants, abbreviations, related terms, and different name.
            2. Include lowercase and uppercase versions.
            3. Include the individual parts of the product name if meaningful (e.g., just "HDPE", just "Regrind").
            4. Do not include any explanations — only the list.
        """
        return f"All different names for {product_name}.", INSTRUCTION
