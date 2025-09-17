from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    crm_phone = fields.Char(string="Lead Phone")
    stop_conversation = fields.Boolean(string="Stop Conversation")
