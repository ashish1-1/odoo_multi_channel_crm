from odoo import fields, models
from werkzeug.urls import url_encode
from odoo.http import request
from odoo.exceptions import UserError
import requests


_TWITTER_SCOPE = "tweet.read tweet.write users.read offline.access"

class TwitterIntegration(models.Model):
    _inherit = "multi.channel.crm"

    def _get_channel(self):
        res = super()._get_channel()
        res.append(('twitter', 'Twitter'))
        return res

    def _compute_callback_url(self):
        for rec in self:
            if rec.channel == 'twitter':
                rec.callback_url = rec.get_webhook_url() + f'{rec.id}/twitter'
            else:
                super()._compute_callback_url()

    def twitter_connection(self):
        client_id = self.api_key
        redirect_url = self.redirect_url
        challenge = self.verify_token
        if redirect_url:
            if 'http' == redirect_url.split(":")[0]:
                redirect_url = redirect_url.replace("http", "https")
        request.session['instance_id'] = self.id
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_url,
            'response_type': 'code',
            'scope': _TWITTER_SCOPE,
            'code_challenge':challenge,
            'state':challenge,
            'code_challenge_method':'plain'
        }
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://x.com/i/oauth2/authorize?%s' % url_encode(params),
            'target': 'self'
        }

    def test_twitter_connection(self):
        if not self:
            self = self.env['multi.channel.crm'].search([('channel', '=', 'twitter')], limit=1)
        if not self.access_token:
            raise  UserError("First Click on the Connect Twitter Button")
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.api_key,
        }
        url = 'https://api.x.com/2/oauth2/token'
        response = requests.post(url, data=data, headers={'Content-Type':'application/x-www-form-urlencoded'})
        if response.ok:
            self.access_token = response.json().get('access_token')
            self.refresh_token = response.json().get('refresh_token')
        else:
            raise UserError(response.json())
