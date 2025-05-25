from odoo import models, fields

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
