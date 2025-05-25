from odoo import models, fields

class LeadMapping(models.Model):
    _name = "channel.lead.mapping"
    _description = "Channel Lead Mapping"
    _rec_name = "lead_name"

    lead_id = fields.Many2one(string='Lead', comodel_name='crm.lead', readonly=True)
    channel_id = fields.Many2one(string='Channel',comodel_name='multi.channel.crm', readonly=True)
    lead_name = fields.Char(string='Lead Name', readonly=True)
