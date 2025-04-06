from odoo import api, models, fields
from ..whatsApp_api import WhatsAppApi
import logging

class WhatsAppIntegaration(models.Model):
    _inherit = 'multi.channel.crm'

    whatsApp_webhook_url = fields.Char(string="WhatsApp Webhook URL",)
    phone_number_id = fields.Char(string="Phone Number ID")

    def _get_channel(self):
        res = super()._get_channel()
        res.append(('whatsapp', 'WhatsApp'))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(WhatsAppIntegaration, self).create(vals_list)
        if res:
            url = res.get_base_url()
            res.write({'whatsApp_webhook_url':url})
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