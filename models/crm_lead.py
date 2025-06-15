from odoo import models, fields, api
import logging

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Business related fields
    loading_port = fields.Char(string="POL/POD")
    monthly_quantity = fields.Char(string="Monthly Quantity")
    current_quantity = fields.Char(string="Current quantity")
    loading_weight = fields.Char(string="Loading weight", help="Loading weight in each container")
    target_price = fields.Char(string="Target Price", help="Target price FOB/CNF basis")
    fob_price = fields.Char(string="FOB Price", help="FOB price")
    customer_type = fields.Selection(string='Customer Type', selection=[('buyer', 'Buyer'), ('seller', 'Seller')])

    channel_id = fields.Many2one(comodel_name='multi.channel.crm', string='Source')
    product_ids = fields.Many2many(string='Product List', comodel_name='product.template')

    continent = fields.Char(string="Continent")
    category = fields.Char(string="Category")

    supplier_code = fields.Char(string="Supplier Code")
    offer_code = fields.Char(string="Offer Code")

    def generate_supplier_code(self):
        self.ensure_one()
        supplier_codes = []
        if self.category and self.continent:
            categories = [cat.strip() for cat in self.category.split(',') if cat.strip()]
            for cat in categories:
                seq = self.env['ir.sequence'].next_by_code('crm.lead.supplier_seq')
                code = self.continent[:2].upper() + cat[:2].upper() + seq
                supplier_codes.append(code)
            self.supplier_code = ' '.join(supplier_codes)
        return True
    
    def generate_offer_code(self):
        self.ensure_one()
        offer_codes = []
        if self.supplier_code:
            supplier_code = self.supplier_code
            supplier_code = [sup_code.strip() for sup_code in self.supplier_code.split(' ') if sup_code.strip()]
            for code in supplier_code:
                month = self.create_date.strftime('%m')
                year = self.create_date.strftime('%Y')[-2:]
                seq = self.env['ir.sequence'].next_by_code('crm.lead.offer_seq')
                offer_codes.append(code + month + year + seq) 
            self.offer_code = ' '.join(offer_codes) 
        return True