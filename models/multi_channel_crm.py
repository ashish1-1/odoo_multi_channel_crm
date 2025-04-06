from odoo import models, fields, api
import logging, secrets

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

    name = fields.Char(string='Name', required=True)
    channel = fields.Selection(string='channel',selection='_get_channel')
    url = fields.Char(string='URL')
    email = fields.Char(string='Api User')
    api_key = fields.Char(string='Api Key')
    secret_key = fields.Char(string='Secret Key')
    password = fields.Char(string='Password')
    active = fields.Boolean(default=True)
    state = fields.Selection(STATE, default='draft')
    image = fields.Image(max_width=256, max_height=256)
    verify_token = fields.Char(string='Verify Token', readonly=True)
    auto_evaluate = fields.Boolean(string="Auto Evaluate")
    
    @api.model_create_multi
    def create(self, vals_list):
        res = super(MultiChannelCrm, self).create(vals_list)
        if res:
            token = res._get_verify_token()
            res.write({'verify_token':token})
        return res

    def _get_channel(self):
        return []
    
    def set_to_draft(self):
        self.state = 'draft'

    def connection(self):
        return []

    def _get_verify_token(self):
        return secrets.token_hex(32)

    def get_base_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url') + "/odoo/webhook"
