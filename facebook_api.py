import logging, requests
_logger = logging.getLogger(__name__)
from .ai_msg_clasification.msg_classification import process_message

class FacebookApi:
    
    def __init__(self, channel,channel_id, access_token, api_key, secret_key, fb_page_id):
        self.channel = channel
        self.channel_id = channel_id
        self.insta_app_id = api_key
        self.insta_app_secret = secret_key
        self.access_token = access_token
        self.fb_page_id = fb_page_id
        self.version = "v22.0"
        self.base_url = "https://graph.facebook.com"

    def handle_message(self, data):
        if not data:
            _logger.error(f"FACEBOOK DATA NOT FOUND : {data}")
            return False
        obj = data.get('object')
        result = False
        if obj == 'page':
            entry = data['entry'][0] if data.get('entry') else []
            if not entry:
                _logger.error(f"FACEBOOK ENTRY NOT FOUND : {entry}")
                return False
            if 'changes' in entry:
                # Handle Comment
                result = self.handel_fb_comments(entry)
            if 'messaging' in entry:
                # Handle Message
                result = self.handel_fb_message(entry)
        return result

    def handel_fb_comments(self, entry):
        changes = entry['changes'][0] if entry.get('changes') else []
        if not changes:
            _logger.error("FACEBOOK CHANGES NOT FOUND")
            return False
        field = changes.get('field')
        if field == 'feed':
            value = changes.get('value')
            if 'message' not in value:
                _logger.info("OTHER MEDIA FOUND")
                return False
            item = value.get('item')
            verb = value.get('verb')
            if item == 'comment' and verb == 'add':
                from_id = value.get('from', {}).get('id')
                if from_id != self.fb_page_id:
                    comment_id = value.get('comment_id')
                    message = value.get('message')
                    response_msg = process_message(message, from_id, False, self.channel_id)
                    if not response_msg:
                        _logger.error("NO AI REPONSE FOUND")
                        return False
                    return self.send_comment_message(response_msg, from_id, comment_id)
        return False

    def handel_fb_message(self, entry):
        messaging = entry['messaging'][0] if entry.get('messaging') else []
        if not messaging:
            _logger.error(f"FACEBOOK MESSAGING NOT FOUND : {messaging}")
            return False
        sender_id = messaging.get('sender', {}).get('id')
        if sender_id == self.fb_page_id:
            _logger.info(f"CONNECTED USER ACCOUNT FOUND")
            return False
        message = messaging.get('message',{})
        if 'text' not in message:
            _logger.info(f"OTHER MEDIA FOUND")
            return False
        if not message:
            _logger.error("NO INCOMING MESSAGE FOUND")
        msg_body = message.get('text')
        response_msg = process_message(msg_body, sender_id, False, self.channel_id)
        if not response_msg:
            _logger.error("NO AI REPONSE FOUND")
            return False
        return self.send_message(response_msg, sender_id)

    def send_message(self, message_text, recipient_id):
        url = f"{self.base_url}/{self.version}/me/messages?access_token={self.access_token}"
        payload = {
            "recipient": {
                "id": recipient_id
            },
            "message": {
                "text": message_text
            },
            "messaging_type": "RESPONSE"
        }
        try:
            response = requests.post(url, json=payload)
        except Exception as e:
            _logger.error(f"SEND MESSAGE EXCEPTION ERROR : {e}")
            return False
        if response.ok:
            _logger.info(f"SUCCESSFULLY FACEBOOK MESSAGE SEND : {response.status_code}")
            return True
        _logger.error(f"FACEBOOK RESPONSE ERROR : {response.json()}")
        return False

    def send_comment_message(self, response_msg, from_id, comment_id):
        url = f"{self.base_url}/{self.version}/{comment_id}/comments"
        payload = {
            "message": response_msg,
            "access_token": self.access_token
        }
        try:
            response = requests.post(url, params=payload)
        except Exception as e:
            _logger.error(f"SEND COMMENT MESSAGE EXCEPTION ERROR : {e}")
            return False
        if response.ok:
            _logger.info(f"SUCCESSFULLY FACEBOOK COMMENT MESSAGE SEND : {response.status_code}")
            return True
        _logger.error(f"FACEBOOK COMMENT RESPONSE ERROR : {response.json()}")
        return False