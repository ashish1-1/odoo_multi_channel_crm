from odoo import models, fields
from odoo.http import request
from werkzeug.urls import url_encode
from ..facebook_api import FacebookApi
import requests
import logging
_logger = logging.getLogger(__name__)



_FACEBOOK_SCOPE = "pages_show_list pages_manage_posts pages_read_engagement pages_manage_metadata pages_messaging pages_manage_engagement"

class FacebookIntegration(models.Model):
    _inherit = "multi.channel.crm"

    fb_page_id = fields.Many2one(string='Facebook Page', comodel_name='facebook.page')
    
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

    def get_facebook_api(self):
        channel = self
        channel_id = self.id
        access_token = self.fb_page_id.access_token
        api_key = self.api_key
        secret_key = self.secret_key
        fb_page_id = self.fb_page_id.page_id
        return FacebookApi(channel=channel, channel_id=channel_id, access_token=access_token, api_key=api_key, secret_key=secret_key, fb_page_id=fb_page_id)

    def get_facebook_page(self):
        url = f"https://graph.facebook.com/v22.0/me/accounts?access_token={self.access_token}"
        msg = ""
        try:
            response = requests.get(url=url)
            data = response.json()
        except Exception as e:
            _logger.error(f"Erro EXCEPTION FOR PAGE : {e}")
            msg = "ERROR EXCEPTION FOUND"
        if 'error' in data:
            _logger.error(f"ERROR FROM PAGE RESPONSE : {data}")
            msg = "ERROR FOUND"
        if response.ok:
            vals = []
            fb_obj = self.env['facebook.page']
            msg = "PAGE UPDATED"
            for page in data.get('data',[]):
                match = fb_obj.search([('page_id', '=', page.get('id'))], limit=1)
                if match:
                    match.write({'access_token':page.get('access_token')})
                else:
                    vals.append({
                        'name':page.get('name'),
                        'page_id':page.get('id'),
                        'access_token':page.get('access_token')
                    })
            if vals:
                rec = self.env['facebook.page'].create(vals)
                msg = f"PAGE CRETAED {rec.ids}"

        return{
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': msg,
            }
        }

class FacebookPage(models.Model):
    _name = "facebook.page"
    _description = "FaceBook Page"

    name = fields.Char(string="Page Name")
    access_token = fields.Char(string="Page Access Token")
    page_id = fields.Char(string="Page ID")
