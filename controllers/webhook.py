from odoo import http
from odoo.http import request
import logging, json, re
from ..whatsApp_api import WhatsAppApi
import base64

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
        try:
            data = request.httprequest.data

            if not data or not channel_id:
                logging.info(f"===================== Missing data or channel ID")
                return {"status": "ignored", "reason": "Missing data or channel ID"}

            if data and channel_id:
                channel = request.env['multi.channel.crm'].sudo().browse(channel_id)
                json_data = json.loads(data.decode('utf-8'))
                if platform == 'whatsapp':
                    # logging.info(f"-------------------{json_data}")
                    whatsapp_api = channel.get_whatsApp_api()
                    return whatsapp_api.handle_message(json_data)
                if platform == 'gmail':
                    print(f"---------------{request.__dir__()}")
                    encoded_data = json_data.get('message').get('data')
                    subscription = json_data.get('subscription')
                    if subscription != channel.subscription:
                        logging.info("================== Subscription mismatch")
                        return {"status": "ignored", "reason": "Subscription mismatch"}
                    if not encoded_data:
                        logging.info("================== Message Id not found")
                        return {"status": "ignored", "reason": "Message Id not found"}
                    log_model = request.env['gmail.webhook.log'].sudo()
                    if log_model.search([('message_id', '=', encoded_data)], limit=1):
                        logging.info("================== Duplicate Message")
                        return {"status": "duplicate", "message_id": encoded_data}
                    log_model.create({'message_id': encoded_data})
                    logging.info(f"===================== Gmail Webhook received")
                    # TODO: Process message here
                    logging.info(f"===================== {json.dumps(json_data, indent=4)}")
                    gmail_api = channel.get_gmail_api()
                    return gmail_api.handle_message(json_data)

        except Exception as e:
            logging.info(f"===================== Error :", str(e))
            return {"status": "error", "detail": str(e)}


# Gmail Webhook Data:
"""
{
    'message': {
        'data': 'eyJlbWFpbEFkZHJlc3MiOiJkZW1vb2RvbzI5QGdtYWlsLmNvbSIsImhpc3RvcnlJZCI6MzUxMH0=',
        'messageId': '13929224991390464',
        'message_id': '13929224991390464',
        'publishTime': '2025-04-18T14:12:54.058Z',
        'publish_time': '2025-04-18T14:12:54.058Z'
    },
    'subscription': 'projects/lucid-mariner-457114-e3/subscriptions/odoo'
}
"""
