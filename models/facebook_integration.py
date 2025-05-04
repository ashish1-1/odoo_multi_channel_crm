from odoo import models, fields
from odoo.http import request
from werkzeug.urls import url_encode

_FACEBOOK_SCOPE = "pages_show_list pages_manage_posts pages_read_engagement pages_manage_metadata"

class FacebookIntegration(models.Model):
    _inherit = "multi.channel.crm"

    def _get_channel(self):
        res = super()._get_channel()
        res.append(('fb', 'Facebook'))
        return res

    def _compute_callback_url(self):
        for rec in self:
            if rec.channel == 'fb':
                rec.callback_url = rec.get_webhook_url() + f'{rec.id}/facebook'
            else:
                super()._compute_callback_url()

    def fb_connection(self):
        client_id = self.api_key
        redirect_url = self.redirect_url
        if redirect_url:
            if 'http' == redirect_url.split(":")[0]:
                redirect_url = redirect_url.replace("http", "https")
        request.session['instance_id'] = self.id
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_url,
            'response_type': 'code',
            'scope': _FACEBOOK_SCOPE,
        }
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.facebook.com/v22.0/dialog/oauth?%s' % url_encode(params),
            'target': 'self'
        }