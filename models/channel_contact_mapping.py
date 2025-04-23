from odoo import models, fields

class ContactMapping(models.Model):
    _name = "channel.contact.mapping"
    _description = "Channel Contact Mapping"

    partner_id = fields.Many2one(string='Partner', comodel_name='res.partner', readonly=True)
    store_partner_id = fields.Char(string='Store Partner ID', readonly=True)
    channel_id = fields.Many2one(string='Channel',comodel_name='multi.channel.crm', 
    readonly=True 
    )
