from odoo import models, fields
from werkzeug.urls import url_encode
from odoo.http import request
from odoo.exceptions import UserError
from ..instagram_api import InstagramApi
import requests


_INSTA_SCOPE = "instagram_business_basic instagram_business_manage_messages instagram_business_manage_comments instagram_business_content_publish instagram_business_manage_insights"

class InstagramIntegration(models.Model):
    _inherit = 'multi.channel.crm'

    ig_account_id = fields.Char(string="Instagram Account ID")

    def _get_channel(self):
        res = super()._get_channel()
        res.append(('insta', 'Instagram'))
        return res

    def _compute_callback_url(self):
        for rec in self:
            if rec.channel == 'insta':
                rec.callback_url = rec.get_webhook_url() + f'{rec.id}/instagram'
            else:
                super()._compute_callback_url()

    def insta_connection(self):
        client_id = self.api_key
        redirect_url = self.redirect_url
        if redirect_url:
            if 'http' == redirect_url.split(":")[0]:
                redirect_url = redirect_url.replace("http", "https")
        request.session['instance_id'] = self.id
        params = {
            'enable_fb_login':0,
            'force_authentication':1,
            'client_id': client_id,
            'redirect_uri': redirect_url,
            'response_type': 'code',
            'scope': _INSTA_SCOPE,
        }
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://api.instagram.com/oauth/authorize?%s' % url_encode(params),
            'target': 'self'
        }

    def test_insta_connection(self):
        if not self:
            self = self.env['multi.channel.crm'].search([('channel', '=', 'insta')], limit=1)
        if not self.access_token:
            raise  UserError("First Click on the Connect Instagram Button")
        data = {
            'grant_type': 'ig_refresh_token',
            'access_token': self.access_token,
        }
        url = 'https://graph.instagram.com/refresh_access_token?%s' % url_encode(data)
        response = requests.get(url=url)
        if response.ok:
            access_token = response.json().get('access_token')
            self.access_token = access_token
        else:
            raise UserError(response.json())

    def get_instagram_api(self):
        channel = self
        channel_id = self.id
        access_token = self.access_token
        api_key = self.api_key
        secret_key = self.secret_key
        ig_account = self.ig_account_id
        return InstagramApi(env=self.env, channel=channel, channel_id=channel_id, access_token=access_token, api_key=api_key, secret_key=secret_key, ig_account=ig_account)
