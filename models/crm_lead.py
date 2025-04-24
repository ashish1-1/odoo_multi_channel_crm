from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Business related fields
    loading_port = fields.Char(string="Loading Port")
    monthly_quantity = fields.Char(string="Monthly Quantity")
    current_quantity = fields.Char(string="Current quantity")
    loading_weight = fields.Char(string="Loading weight", help="Loading weight in each container")
    taregt_price = fields.Char(string="Taregt Price", help="Taregt price FOB/CNF basis")
    customer_type = fields.Selection(string='Customer Type',selection=[('buyer', 'Buyer'), ('seller', 'Seller')])