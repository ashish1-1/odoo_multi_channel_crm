from odoo import api, models, fields
from ..whatsApp_api import WhatsAppApi
from odoo.exceptions import UserError
import logging

class WhatsAppIntegaration(models.Model):
    _inherit = 'multi.channel.crm'

    phone_number_id = fields.Char(string="Phone Number ID")
    account_uid = fields.Char(string="Account ID")
    app_uid = fields.Char(string="App ID")
    callback_url = fields.Char(string="Callback URL", compute='_compute_callback_url', readonly=True, copy=False)

    def _compute_callback_url(self):
        for account in self:
            account.callback_url = self.base_url() + f'/odoo/webhook/{account.id}/whatsapp'

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
        account_uid = self.account_uid
        app_uid = self.app_uid
        return WhatsAppApi(channel, channel_id, access_token, phone_number_id, app_uid, account_uid)

    def test_whatsapp_connection(self):
        """ Test connection of the WhatsApp Business Account. with the given credentials.
        """
        self.ensure_one()
        wa_api = self.get_whatsApp_api()
        try:
            wa_api._test_connection()
            self.state = 'connected'
        except Exception as e:
            raise UserError(str(e))
        return True
