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

    lead_type_id = fields.Many2one(
        comodel_name='lead.type',
        string='Lead Type'
    )
    categ_ids = fields.Many2many(
        comodel_name='categ.categ',
        string='Category'
    )
    sub_categ_ids = fields.Many2many(
        comodel_name='sub.categ',
        string='Sub Category'
    )
    child_categ_ids = fields.Many2many(
        comodel_name='child.categ',
        string='Child Category'
    )
    sub_child_categ_ids = fields.Many2many(
        comodel_name='sub.child.categ',
        string='Sub Child Category'
    )
    form_ids = fields.Many2many(
        comodel_name='form.form',
        string='Form'
    )
    channel_id = fields.Many2one(
        comodel_name='multi.channel.crm',
        string='Source'
    )
