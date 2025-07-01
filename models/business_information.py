from odoo import models, fields

class BusinessInformation(models.Model):
    _name="business.information"
    _description="Business Information"

    product = fields.Char(string="Product")
    loading_port = fields.Char(string="POL/POD")
    monthly_quantity = fields.Char(string="Monthly Quantity")
    current_quantity = fields.Char(string="Current quantity")
    loading_weight = fields.Char(string="Loading weight", help="Loading weight in each container")
    target_price = fields.Char(string="Target Price", help="Target price")
    fob_price = fields.Char(string="FOB Price", help="FOB price")

    # Product related information fields
    category = fields.Char(string="Categroy")
    forms = fields.Char(string="Forms")

    kyc_feed_id = fields.Many2one(
        string='Feed ID',
        comodel_name='kyc.feed',
    )
    