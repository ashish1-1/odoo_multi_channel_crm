from odoo import models, fields
from werkzeug.urls import url_encode
from odoo.http import request
from odoo.exceptions import UserError
import requests


_INSTA_SCOPE = "instagram_business_basic instagram_business_manage_messages instagram_business_manage_comments instagram_business_content_publish instagram_business_manage_insights"

class InstagramIntegration(models.Model):
    _inherit = 'multi.channel.crm'


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
            'url': 'https://www.instagram.com/oauth/authorize?%s' % url_encode(params),
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