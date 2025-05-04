from odoo import http
from odoo.http import request
import logging, requests, base64
from werkzeug.utils import redirect
from odoo.exceptions import UserError
from werkzeug.urls import url_encode

_logger = logging.getLogger(__name__)

class ChannelWebhook(http.Controller):

    @http.route('/channel/redirect', type='http', auth='public', methods=['GET'], csrf=False)
    def connection(self, **kwargs):
        channel_id = request.session.get('instance_id')
        if channel_id and kwargs:
            channel = request.env['multi.channel.crm'].browse(channel_id)
            if channel.channel == 'gmail':
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
            elif channel.channel == 'linkedIn':
                state = request.session.get('state')
                if kwargs.get('error') not in ('user_cancelled_authorize', 'user_cancelled_login'):
                    code = kwargs.get('code')
                    access_token = kwargs.get('access_token')
                    if not access_token and not code:
                        _logger.error('======LinkedIn did not provide a valid access token.')
                        return {'error_message': 'LinkedIn did not provide a valid access token.'}

                    if state != kwargs.get('state'):
                        _logger.error('=======There was a authentication issue during your request.')
                        return {'error_message': 'There was a authentication issue during your request.'}

                try:
                    if not access_token:
                        access_token = self._linkedin_get_access_token(code, channel.api_key, channel.secret_key, channel.redirect_url)
                        channel.write({
                        'access_token':access_token,
                        'state':'connected',
                        })
                except Exception as e:
                    _logger.error(f"Error Message : {e}")
                    channel.write({'state':'error'})
                    return "<h2>LinkedIn Auth Failed</h2><p>{}</p>".format(e)
            elif channel.channel == 'insta':
                code = kwargs.get('code')
                access_token = self._get_insta_short_live_access_token(code, channel.api_key, channel.secret_key, channel.redirect_url)
                if access_token:
                    channel.write({
                            'access_token':access_token,
                            'state':'connected',
                        })
            elif channel.channel == 'fb':
                code = kwargs.get('code')
                access_token = self._get_facebook_short_live_access_token(code, channel.api_key, channel.secret_key, channel.redirect_url)
                if access_token:
                    channel.write({
                            'access_token':access_token,
                            'state':'connected',
                        })
            elif channel.channel == 'twitter':
                state = kwargs.get('state')
                code = kwargs.get('code')
                if state == channel.verify_token:
                    access_token = self._get_twitter_access_token(code, channel.api_key, channel.secret_key, channel.redirect_url, channel.verify_token)
            else:
                logging.info("=================No CHANNEL FOUND FOR THE REDIRECT")
        action_id = request.env.ref('odoo_multi_channel_crm.multi_channel_crm_view_action').id
        return redirect(f"/web#id={channel_id}&action={action_id}&model=multi.channel.crm&view_type=form")     

    def _linkedin_get_access_token(self, linkedin_authorization_code, client_id, client_secret, redirect_url):
        """
        Take the `authorization code` and exchange it for an `access token`
        We also need the `redirect uri`

        :return: the access token
        """
        linkedin_url = 'https://www.linkedin.com/oauth/v2/accessToken'
        linkedin_app_id = client_id
        linkedin_client_secret = client_secret
        redirect_uri = redirect_url

        params = {
            'grant_type': 'authorization_code',
            'code': linkedin_authorization_code,
            'redirect_uri': redirect_uri,
            'client_id': linkedin_app_id,
            'client_secret': linkedin_client_secret
        }

        response = requests.post(linkedin_url, data=params, timeout=5).json()

        error_description = response.get('error_description')
        if error_description:
            raise UserError(error_description)

        return response.get('access_token')

    def _get_insta_short_live_access_token(self, code, client_id, client_secret, redirect_uri):
        token_url = 'https://api.instagram.com/oauth/access_token'
        params = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
        try:
            response = requests.post(token_url, data=params)
            data = response.json()
        except Exception as e:
            _logger.error(f"Exception Raise From Short-live Token : {e}")
            return ''
        if 'error' in data:
            _logger.error(f"Error Message From Instagram Short-live Access Token : {data.get('error',{}).get('message')}")
            return ''
        if response.ok:
            access_token = data.get('access_token')
            if access_token:
                long_live_token = self._get_insta_long_live_access_token(access_token, client_secret)
            return long_live_token

    def _get_insta_long_live_access_token(self, token, client_secret):
        url = "https://graph.instagram.com/access_token"
        params = {
            'grant_type': 'ig_exchange_token',
            'client_secret': client_secret,
            'access_token': token
        }
        try:
            response = requests.get(url + '?' + url_encode(params))
            data = response.json()
        except Exception as e:
            _logger.error(f"Exception Raise From Long-live Token : {e}")
            return ''
        if 'error' in data:
            _logger.error(f"Error Message From Instagram long-live Access Token : {data.get('error',{}).get('message')}")
            return ''
        if response.ok:
            access_token = data.get('access_token')
            return access_token

    def _get_facebook_short_live_access_token(self, code, client_id, client_secret, redirect_uri):
        token_url = 'https://graph.facebook.com/v22.0/oauth/access_token'
        params = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
        }
        try:
            response = requests.get(token_url + '?' + url_encode(params))
            data = response.json()
        except Exception as e:
            _logger.error(f"Exception Raise From FaceBook Token : {e}")
            return ''
        if 'error' in data:
            _logger.error(f"Error Message From Facebook Access Token : {data.get('error',{}).get('message')}")
            return ''
        if response.ok:
            access_token = data.get('access_token')
            if access_token:
                long_live_token = self._get_facebook_long_live_access_token(access_token, client_id, client_secret)
            return long_live_token

    def _get_facebook_long_live_access_token(self, access_token, client_id, client_secret):
        token_url = 'https://graph.facebook.com/v22.0/oauth/access_token'
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id':client_id,
            'client_secret': client_secret,
            'fb_exchange_token': access_token
        }
        try:
            response = requests.get(token_url + '?' + url_encode(params))
            data = response.json()
        except Exception as e:
            _logger.error(f"Exception Raise From FaceBook Token : {e}")
            return ''
        if 'error' in data:
            _logger.error(f"Error Message From Facebook Access Token : {data.get('error',{}).get('message')}")
            return ''
        if response.ok:
            token = data.get('access_token')
            return token

    def _get_twitter_access_token(self, code, client_id, client_secret, redirect_uri, code_verifier):
        url = "https://api.x.com/2/oauth2/token"
        credentials = f"{client_id}:{client_secret}"
        data = {
            'grant_type':'authorization_code',
            'code':code,
            'redirect_uri':redirect_uri,
            'client_id':client_id,
            'code_verifier':code_verifier,
            'Authorization':'Basic '+base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        }
        try:
            response = requests.post(url, data=data, headers={'Content-Type':'application/x-www-form-urlencoded'})
            data = response.json()
        except Exception as e:
            _logger.error(f"Exception Raise From Twitter Token : {e}")
            return ''
        if 'error' in data:
            _logger.error(f"Error Message From Twitter Access Token : {data}")
            return ''
        if response.ok:
            token = data.get('access_token')
            return token
