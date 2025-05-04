from odoo import fields, models
from werkzeug.urls import url_encode
from odoo.http import request


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
            'url': 'https://twitter.com/i/oauth2/authorize?%s' % url_encode(params),
            'target': 'self'
        }