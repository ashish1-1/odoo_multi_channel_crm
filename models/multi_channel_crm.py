from odoo import models, fields
import logging

STATE = [
    ('draft', 'Draft'),
    ('connected', 'Connected'),
    ('error', 'Error')
]

DEBUG = [
    ('enable', 'Enable'),
    ('disable', 'Disable')
]

class MultiChannelCrm(models.Model):
    _name = 'multi.channel.crm'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Mutli Channel Crm"

    name = fields.Char(string='Name')
    channel = fields.Selection(
        string='channel',
        selection='_get_channel'
    )
    url = fields.Char(string='URL')
    email = fields.Char(string='Api User')
    api_key = fields.Char(string='Api Key')
    secret_key = fields.Char(string='Secret Key')
    password = fields.Char(string='Password')
    active = fields.Boolean(default=True)
    state = fields.Selection(STATE, default='draft')
    image = fields.Image(max_width=256, max_height=256)
    

    def _get_channel(self):
        return []
    
    def set_to_draft(self):
        self.state = 'draft'

    def connection(self):
        return []