from odoo import models, fields, api
from odoo.exceptions import UserError
from markupsafe import Markup


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    business_info_ids = fields.One2many(string='Business Information', comodel_name='business.information', inverse_name='lead_id')
    seller_offer_code_ids = fields.One2many(string='Seller Offer Code', comodel_name='seller.offer.code', inverse_name='lead_id')
    customer_type = fields.Selection(string='Customer Type', selection=[('buyer', 'Buyer'), ('seller', 'Seller')])

    channel_id = fields.Many2one(comodel_name='multi.channel.crm', string='Media Source')
    product_ids = fields.Many2many(string='Product List', comodel_name='product.template')

    continent = fields.Char(string="Continent")

    supplier_code = fields.Char(string="Supplier Code")

    def generate_supplier_code(self):
        self.ensure_one()
        categories = list(set(self.business_info_ids.mapped('category')))
        if not self.continent or not categories:
            raise UserError("Continent or categories missing from business info.")

        supplier_codes = []
        for cat in categories:
            if not cat:
                continue
            seq = self.env['ir.sequence'].next_by_code('crm.lead.supplier_seq')
            code = self.continent[:2].upper() + cat[:2].upper() + seq
            supplier_codes.append(code)

        # Join all generated supplier codes (in case multiple categories exist)
        self.supplier_code = ''.join(supplier_codes)
        return self.supplier_code


    def generate_offer_codes(self):
        self.ensure_one()

        if not self.supplier_code:
            raise UserError("Supplier code missing. Please generate it first.")
        if not self.product_ids:
            raise UserError("No products linked to this lead.")

        supplier_code = self.supplier_code

        self.seller_offer_code_ids.unlink()

        for product in self.product_ids:
            month = self.create_date.strftime('%m')
            year = self.create_date.strftime('%Y')[-2:]
            seq = self.env['ir.sequence'].next_by_code('crm.lead.offer_seq')
            offer_code = supplier_code + month + year + seq

            # Try to fetch monthly quantity, weight from business_info_ids by product match
            related_info = self.business_info_ids.filtered(
                lambda b: b.product and b.product.lower() in [product.name.lower(), product.default_code.lower()]
            )
            monthly_quantity = related_info[0].monthly_quantity if related_info else ''
            loading_weight = related_info[0].loading_weight if related_info else ''

            self.env['seller.offer.code'].create({
                'supplier_code': supplier_code,
                'offer_code': offer_code,
                'product_id': product.id,
                'continent': self.continent,
                'lead_id': self.id,
                'monthly_quantity': monthly_quantity,
                'loading_weight': loading_weight,
            })

    def get_matching_seller_offers(self):
        self.ensure_one()

        matched_offers = []

        for product in self.product_ids:
            # Find matching offers by product
            offers = self.env['seller.offer.code'].search([
                ('product_id', '=', product.id),
            ])

            for offer in offers:
                matched_offers.append({
                    'offer_code': offer.offer_code,
                    'product': offer.product_id.name,
                    'category': offer.category,
                    'form': offer.form,
                    'supplier_code': offer.supplier_code,
                    'monthly_quantity': offer.monthly_quantity,
                    'loading_weight': offer.loading_weight,
                    'continent': offer.continent,
                })

        return matched_offers

    def prepare_offer_email_for_buyer(self, offers_data):
        self.ensure_one()

        if not offers_data:
            raise UserError("No matching seller offers found for this lead.")

        # 1. Subject
        product = [data['product'] for data in offers_data]
        main_product = ', '.join(product)
        ref_code = offers_data[0]['supplier_code']
        subject = f"Offering {main_product} (Ref. no {ref_code}) - FOUR SEASONS FZE"
        return {
            'subject': subject,
        }

    def _build_html_offer_email(self, offers_data):
        intro = """
        <p>Hello,</p>
        <p>This side is <strong>Anshul Goel</strong> from <strong>Four Seasons FZE</strong>. We are dealing in various materials including metals, plastics, textiles for primary & secondary forms including post industrial wastes. We have multiple collaborating companies for all our materials in various parts of the globe including Germany, Netherlands, Italy, Japan, Korea, USA and so on.</p>
        """

        offer_blocks = ""
        for idx, offer in enumerate(offers_data, 1):
            offer_blocks += f"""
            <h4>Material {idx}: {offer['product']}</h4>
            <ul>
                <li><strong>Industry:</strong> {offer['category']} production</li>
                <li><strong>Offer Code:</strong> {offer['offer_code']}</li>
                <li><strong>Monthly Quantity:</strong> {offer['monthly_quantity']} tons +/-</li>
                <li><strong>Loading Weight:</strong> {offer['loading_weight'] or '21'} tons +/-</li>
                <li><strong>Origin:</strong> {offer['continent']}</li>
            </ul>
            <br/>
            """

        delivery = """
        <h4>Delivery Notes:</h4>
        <ul>
            <li><strong>Price:</strong> Kindly share your best price with the destination port.</li>
            <li><strong>Payment Terms:</strong> 50% advance within 3 days of confirmation – 50% within 3 days after sharing loading pictures / B/L draft copy by email.</li>
            <li><strong>Inspection:</strong> Not Allowed</li>
        </ul>
        <p>Attached pictures for ref.</p>

        <h4>Notes:</h4>
        <ol>
            <li>We do not deal on CAD, DP, L/C basis.</li>
            <li>We sell material as per picture basis.</li>
            <li>All our offers are subject to reconfirmation.</li>
        </ol>
        """

        return Markup(f"""
        <div style="font-family: Arial, sans-serif; font-size: 14px;">
            {intro}
            {offer_blocks}
            {delivery}
        </div>
        """)
