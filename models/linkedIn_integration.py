from odoo import models, fields
from odoo.http import request
from werkzeug.urls import url_encode
import uuid


_LINKEDIN_SCOPE = 'w_member_social r_events'

class LinkedInIntegration(models.Model):
    _inherit = "multi.channel.crm"

    def _get_channel(self):
        res = super()._get_channel()
        res.append(('linkedIn', 'LinkedIn'))
        return res

    def _compute_callback_url(self):
        for rec in self:
            if rec.channel == 'linkedIn':
                rec.callback_url = rec.get_webhook_url() + f'{rec.id}/linkedIn'
            else:
                super()._compute_callback_url()

    def test_linkedIn_connection(self):
        client_id = self.api_key
        redirect_url = self.redirect_url
        state = str(uuid.uuid4().int)[:8]
        request.session['instance_id'] = self.id
        request.session['state'] = state
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_url,
            'state': state,
            'scope': _LINKEDIN_SCOPE,
        }
        print(params)
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.linkedin.com/oauth/v2/authorization?%s' % url_encode(params),
            'target': 'self'
        }
