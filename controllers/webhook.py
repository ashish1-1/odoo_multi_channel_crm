from odoo import http
from odoo.http import request
import logging, json
import base64

_logger = logging.getLogger(__name__)



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
                    logging.info(f"================ WEBHOOK_VERIFIED === {platform}")
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
                _logger.info(f"===================== Missing data or channel ID")
                return {"status": "ignored", "reason": "Missing data or channel ID"}
            
            channel = request.env['multi.channel.crm'].sudo().browse(channel_id)
            if not channel.exists() and channel.state != 'connected':
                _logger.info("Invalid Channel ID Or Not Connected")
                return {"status": "ignored", "reason": "Invalid Channel ID"}

            json_data = json.loads(data.decode('utf-8'))
            # logging.info(f"-------------------{json_data}")
            if platform == 'whatsapp':
                whatsapp_api = channel.get_whatsApp_api()
                whatsapp_api.handle_message(json_data)
                return http.Response(status=200)
            elif platform == 'gmail':
                result = self.gmail_webhook_process(channel, json_data)
                if not result.get('status'):
                    return http.Response(status=500)
                vals = {
                    'msg_json_data':json_data,
                    'decode_info':result.get('decoded_data'),
                    'history_id':result.get('decoded_data',{}).get('historyId')
                }

                request.env['gmail.webhook.data'].sudo().create(vals)
                return http.Response(status=200)
            elif platform == 'instagram':
                instagram_api = channel.get_instagram_api()
                instagram_api.handle_message(json_data)
                return http.Response(status=200)
            elif platform == 'facebook':
                facebook_api = channel.get_facebook_api()
                facebook_api.handle_message(json_data)
                return http.Response(status=200)
            else:
                _logger.info("Unknown platform: %s", platform)
                _logger.info("json_data: %s", json_data)
                return {"status": "ignored", "reason": "Unknown platform"}

        except Exception as e:
            _logger.exception(f"Webhook error occurred : {str(e)}")
            return {"status": "error", "detail": str(e)}

    def gmail_webhook_process(self, channel, json_data):
        encoded_data = json_data.get('message').get('data')
        subscription = json_data.get('subscription')
        message = "Sucessfull process"
        decoded_data = {}
        if subscription != channel.subscription:
            _logger.info("================== Subscription mismatch")
            return {
                'status':False,
                'decoded_data':decoded_data,
                'message':"Error processing webhook",
            }
        try:
            decoded_data = json.loads(base64.urlsafe_b64decode(encoded_data).decode('utf-8'))
        except Exception as decode_error:
            _logger.exception("Failed to decode Pub/Sub data")
            return {
                'status':False,
                'decoded_data':decoded_data,
                'message':"Failed to decode Pub/Sub data:\n {}".format(str(decode_error)),
            }
        _logger.info(f"===================== Gmail Webhook received")
        return {
            'status':True,
            'decoded_data':decoded_data,
            'message':message,
        }
