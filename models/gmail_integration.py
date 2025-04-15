from odoo import models, fields
from odoo.http import request
from urllib.parse import urlencode
import requests
from odoo.exceptions import UserError

SCOPE = "https://www.googleapis.com/auth/gmail.send"

class GmailIntegration(models.Model):
    _inherit = 'multi.channel.crm'

    def _get_channel(self):
        res = super()._get_channel()
        res.append(('gmail', 'Gmail'))
        return res

    def test_gmail_connection(self):
        if not self.refresh_token:
            raise  UserError("First Click on the Connect Gmail Button")
        url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': self.api_key,
            'client_secret': self.secret_key,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token',
        }
        response = requests.post('https://oauth2.googleapis.com/token', data=data)
        if response.ok:
            access_token = response.json().get('access_token')
            self.access_token = access_token
        else:
            print("Error:", response.json())

    def gmail_connection(self):
        client_id = self.api_key
        redirect_url = self.redirect_url
        if redirect_url:
            if 'http' == redirect_url.split(":")[0]:
                print("inside")
                redirect_url = redirect_url.replace("http", "https")

        request.session['instance_id'] = self.id
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_url,
            'scope': SCOPE,
            'access_type': 'offline',
            'prompt': 'consent',
        }
        full_url = f"{base_url}?{urlencode(params)}"
        print(full_url)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': full_url,
        }
