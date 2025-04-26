from odoo import models, fields
from odoo.http import request
from urllib.parse import urlencode
from odoo.exceptions import UserError
from ..gmail_api import GmailApi
import requests

import logging
_logger = logging.getLogger(__name__)



SCOPE = "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly"

class GmailIntegration(models.Model):
    _inherit = 'multi.channel.crm'

    topic = fields.Char(string="Topic")
    subscription = fields.Char(string="Subscription")
    project_id = fields.Char(string="Project ID")

    def _get_channel(self):
        res = super()._get_channel()
        res.append(('gmail', 'Gmail'))
        return res

    def _compute_callback_url(self):
        for rec in self:
            if rec.channel == 'gmail':
                rec.callback_url = rec.get_webhook_url() + f'{rec.id}/gmail'
            else:
                super()._compute_callback_url()

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

    def setup_gmail_watch_topic(self, cron=False):
        """Registers Gmail account to watch for changes and push to Pub/Sub topic."""
        if cron:
            self = self.env['multi.channel.crm'].search([('channel', '=', 'gmail')], limit=1)

        if not (self.access_token and self.topic):
            _logger.error("Api key and topic is missing")
            return None

        url = " https://gmail.googleapis.com/gmail/v1/users/me/watch"
        header = {
            'Authorization': f"Bearer {self.access_token}",
            'Content-Type': 'application/json'
        }
        payload =  {
        "topicName": self.topic,
        "labelIds": ["INBOX"]
        }
        try:
            response = requests.post(url=url, headers=header, json=payload)
            response.raise_for_status()  # Raise an error for HTTP errors

            data = response.json()
            _logger.info("Gmail watch successfully created: %s", data)
            return data

        except requests.exceptions.HTTPError as http_err:
            _logger.error("HTTP error while setting up Gmail watch: %s - %s", http_err, response.text)
        except requests.exceptions.RequestException as req_err:
            _logger.error("Request error while setting up Gmail watch: %s", req_err)
        except Exception as e:
            _logger.exception("Unexpected error while setting up Gmail watch: %s", e)
        return None

    def open_cron_view(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.cron',
            'res_id':self.env.ref('odoo_multi_channel_crm.setup_gmail_watch_topic').id,
            'view_mode': 'form',
            'target': 'self',
        }

    def get_gmail_api(self):
        channel = self
        channel_id = self.id
        access_token = self.api_key
        return GmailApi(channel, channel_id, access_token)
