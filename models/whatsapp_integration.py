from odoo import api, models, fields
from ..whatsApp_api import WhatsAppApi
import logging

class WhatsAppIntegaration(models.Model):
    _inherit = 'multi.channel.crm'

    phone_number_id = fields.Char(string="Phone Number ID", required=True)
    account_uid = fields.Char(string="Account ID", required=True)
    app_uid = fields.Char(string="App ID", required=True)
    callback_url = fields.Char(string="Callback URL", compute='_compute_callback_url', readonly=True, copy=False)

    def _compute_callback_url(self):
        for account in self:
            account.callback_url = self.base_url() + '/whatsapp/webhook'

    def _get_channel(self):
        res = super()._get_channel()
        res.append(('whatsapp', 'WhatsApp'))
        return res

    def get_base_url(self):
        res = super(WhatsAppIntegaration, self).get_base_url()
        if res:
            return res+f"/{self.id}/whatsapp"
        return res

    def get_whatsApp_api(self):
        channel = self
        channel_id = self.id
        access_token = self.api_key
        phone_number_id = self.phone_number_id
        return WhatsAppApi(channel, channel_id, access_token, phone_number_id)
