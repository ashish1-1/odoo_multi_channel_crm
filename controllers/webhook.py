from odoo import http
from odoo.http import request
import logging, json, re
from ..whatsApp_api import WhatsAppApi 

class ChannelWebhook(http.Controller):
    @http.route('/odoo/webhook/<int:channel_id>/<string:platform>', type='http', auth='public', methods=['GET'], csrf=False)
    def webhook_get(self ,channel_id, platform, **kwargs):
        mode = kwargs.get("hub.mode")
        token = kwargs.get("hub.verify_token")
        challenge = kwargs.get("hub.challenge")
        if channel_id:
            channel = request.env['multi.channel.crm'].sudo().browse(channel_id)
            if not channel:
                logging.info("============== Channel Not Found")
                return False
            if mode and token:
                if mode == "subscribe" and token == channel.verify_token:
                    logging.info("================ WEBHOOK_VERIFIED")
                    return challenge
                else:
                    # Responds with '403 Forbidden' if verify tokens do not match
                    logging.info("================ VERIFICATION_FAILED")
                    return request.make_response(json.dumps({"status": "error", "message": "Verification failed"}), status=403)
            else:
                # Responds with '400 Bad Request' if verify tokens do not match
                logging.info("================== MISSING_PARAMETER")
                return request.make_response(json.dumps({"status": "error", "message": "Missing parameters"}), status=400)
        else:
            logging.info("==================== Channel ID's Missing")
            return False

    @http.route('/odoo/webhook/<int:channel_id>/<string:platform>', type='json', auth='public', methods=['POST'], csrf=False)
    def webhook_post(self,channel_id, platform, **post):
        data = request.httprequest.data
        if data and platform == "whatsapp":
            json_data = json.loads(data.decode('utf-8'))
            # logging.info(f"-------------------{json_data}")
            whatsapp_api = request.env['multi.channel.crm'].sudo().browse(channel_id).get_whatsApp_api()
            return whatsapp_api.handle_message(json_data)
        return True
