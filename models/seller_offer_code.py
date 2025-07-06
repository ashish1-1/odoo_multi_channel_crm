from odoo import models, fields

class SellerOfferCode(models.Model):
    _name = 'seller.offer.code'
    _description = 'Seller Offer Code'
    _rec_name = 'offer_code'

    supplier_code = fields.Char(string='Supplier Code')
    offer_code = fields.Char(string='Offer Code', required=True)

    product_id = fields.Many2one(string='Product', comodel_name='product.template')
    category = fields.Char(string='Category', related='product_id.crm_categ_id.name')
    form = fields.Char(string='Form', related='product_id.forms_id.name')
    sub_categ = fields.Char(string='Sub Categroy', related='product_id.sub_categ_id.name')

    monthly_quantity = fields.Char(string="Monthly Quantity")
    loading_weight = fields.Char(string="Loading weight", help="Loading weight in each container")

    continent = fields.Char(string='Continent')

    lead_id = fields.Many2one(string='Lead', comodel_name='crm.lead', ondelete='cascade', readonly=True)