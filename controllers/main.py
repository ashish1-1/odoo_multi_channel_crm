from odoo import http
from odoo.http import request
import logging, requests
from werkzeug.utils import redirect

class ChannelWebhook(http.Controller):

    @http.route('/channel/redirect', type='http', auth='public', methods=['GET'], csrf=False)
    def connection(self, **kwargs):
        channel_id = request.session.get('instance_id')
        if channel_id and kwargs:
            channel = request.env['multi.channel.crm'].browse(channel_id)
            auth_code = kwargs.get('code')
            client_id = channel.api_key
            client_secret = channel.secret_key
            redirect_uri = channel.redirect_url
            token_url = 'https://oauth2.googleapis.com/token'
            params = {
                'code': auth_code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            }
            response = requests.post(token_url, data=params)
            if response.status_code in [200]:
                data = response.json()
                access_token = data.get('access_token')
                refresh_token = data.get('refresh_token')
                expires_in = data.get('expires_in')
                channel.write({
                    'access_token':access_token,
                    'refresh_token':refresh_token,
                    'state':'connected',
                })
            action_id = request.env.ref('odoo_multi_channel_crm.multi_channel_crm_view_action').id
        return redirect(f"/web#id={channel_id}&action={action_id}&model=multi.channel.crm&view_type=form")     