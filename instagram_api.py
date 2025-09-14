import logging, requests
from odoo.api import Environment
from .ai_msg_clasification.msg_classification import process_message
_logger = logging.getLogger(__name__)

class InstagramApi:
    
    def __init__(self, env:Environment, channel,channel_id, access_token, api_key, secret_key, ig_account):
        self.channel = channel
        self.channel_id = channel_id
        self.insta_app_id = api_key
        self.insta_app_secret = secret_key
        self.access_token = access_token
        self.ig_account = ig_account
        self.version = "v22.0"
        self.base_url = "https://graph.instagram.com"
        self.env = env

    def handle_message(self, data):
        """
        Handle incoming webhook events from the Instagram API.
        This function processes incoming Instagram messages and other events.
        If the event is a valid message, it gets
        processed. If the incoming payload is not a recognized Instagram event,
        an error is returned.
        Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

        Returns:
            response: A Boolean Value True/False.
        """
        if not data:
            _logger.error(f"INSTAGRAM DATA NOT FOUND : {data}")
            return False
        obj = data.get('object')
        result = False
        if obj == 'instagram':
            entry = data['entry'][0] if data.get('entry') else []
            if not entry:
                _logger.error(f"INSTAGRAM ENTRY NOT FOUND : {entry}")
                return False

            if 'changes' in entry:
                # Handle Comment
                result = self.handel_ig_comments(entry)
            if 'messaging' in entry:
                # Handle Message
                result = self.handel_ig_message(entry)
        return result

    def handel_ig_comments(self, entry):
        changes = entry['changes'][0] if entry.get('changes') else []
        if not changes:
            _logger.error("INSTAGRAM CHANGES NOT FOUND")
            return False
        field = changes.get('field')
        if field == 'comments':
            value = changes.get('value')
            if 'text' not in value:
                _logger.info("OTHER MEDIA FOUND")
                return True 
            from_id = value.get('from', {}).get('id')
            if from_id != self.ig_account:
                parent_comment_id = value.get('id')
                text = value.get('text')
                text = f"""
From : Comment
{text}
"""
                response_msg = process_message(self.env, text, from_id, False, self.channel_id)
                if not response_msg:
                    _logger.error("NO AI REPONSE FOUND")
                    return False
                if self.channel.auto_reply:
                    return self.send_comment_message(response_msg, from_id, parent_comment_id)
                return True
        return False
            
    def handel_ig_message(self, entry):
        messaging = entry['messaging'][0] if entry.get('messaging') else []
        if not messaging:
            _logger.error(f"INSTAGRAM MESSAGING NOT FOUND : {messaging}")
            return False
        sender_id = messaging.get('sender', {}).get('id')
        if sender_id == self.ig_account:
            _logger.info(f"CONNECTED USER ACCOUNT FOUND")
            return False
        message = messaging.get('message',{})
        if 'text' not in message:
            _logger.info(f"OTHER MEDIA FOUND")
            return False
        if not message:
            _logger.error("NO INCOMING MESSAGE FOUND")
        msg_body = message.get('text')
        response_msg = process_message(self.env, msg_body, sender_id, False, self.channel_id)
        if not response_msg:
            _logger.error("NO AI REPONSE FOUND")
            return False
        if self.channel.auto_reply:
            return self.send_message(response_msg, sender_id)
        return True

    def send_message(self, message_text, recipient_id):
        url = f"{self.base_url}/{self.version}/me/messages"
        payload = {
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": message_text
            },
            "messaging_type": "RESPONSE"
        }
        headers = {
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(url, json=payload, headers=headers, params={"access_token": self.access_token})
        except Exception as e:
            _logger.error(f"SEND MESSAGE EXCEPTION ERROR : {e}")
            return False
        if response.ok:
            _logger.info(f"SUCCESSFULLY INSTAGRAM MESSAGE SEND : {response.status_code}")
            return True
        _logger.error(f"INSTAGRAM RESPONSE ERROR : {response.json()}")
        return False

    def send_comment_message(self, message, recipient_id, comment_id):
        url = f"{self.base_url}/{self.version}/{comment_id}/replies"
        payload = {
            "message": message,
            "access_token": self.access_token
        }
        try:
            response = requests.post(url, data=payload)
        except Exception as e:
            _logger.error(f"SEND COMMENT MESSAGE EXCEPTION ERROR : {e}")
            return False
        if response.ok:
            _logger.info(f"SUCCESSFULLY INSTAGRAM COMMENT MESSAGE SEND : {response.status_code}")
            return True
        _logger.error(f"INSTAGRAM COMMENT RESPONSE ERROR : {response.json()}")
        return False
