import logging, json, re, requests
from odoo.http import request
from .ai_msg_clasification.msg_classification import process_message
from odoo.exceptions import UserError

DEFAULT_ENDPOINT = "https://graph.facebook.com"

class WhatsAppApi:
    def __init__(self, channel,channel_id, access_token, phone_number_id, app_uid, account_uid):
        self.channel = channel
        self.channel_id = channel_id
        self.access_token = access_token
        self.version = "v22.0"
        self.phone_number_id = phone_number_id
        self.app_uid = app_uid
        self.account_uid = account_uid


    def handle_message(self, body):
        """
        Handle incoming webhook events from the WhatsApp API.

        This function processes incoming WhatsApp messages and other events,
        such as delivery statuses. If the event is a valid message, it gets
        processed. If the incoming payload is not a recognized WhatsApp event,
        an error is returned.

        Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

        Returns:
            response: A tuple containing a JSON response and an HTTP status code.
        """
        # Check if it's a WhatsApp status update
        if (
            body.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("statuses")
        ):
            logging.info("Received a WhatsApp status update.")
            return request.make_response(json.dumps({"status": "ok"}), status=200)
        try:
            if self.is_valid_whatsapp_message(body):
                self.process_whatsapp_message(body)
                return request.make_response(json.dumps({"status": "ok"}), status=200)
            else:
                # if the request is not a WhatsApp API event, return an error
                return request.make_response(json.dumps({"status": "error", "message": "Not a WhatsApp API event"}),
                    status=404,
                )
        except json.JSONDecodeError:
            logging.error("Failed to decode JSON")
            return request.make_response(json.dumps({"status": "error", "message": "Invalid JSON provided"}), status=400)

    def is_valid_whatsapp_message(self, body):
        """
        Check if the incoming webhook event has a valid WhatsApp message structure.
        """
        return (
            body.get("object")
            and body.get("entry")
            and body["entry"][0].get("changes")
            and body["entry"][0]["changes"][0].get("value")
            and body["entry"][0]["changes"][0]["value"].get("messages")
            and body["entry"][0]["changes"][0]["value"]["messages"][0]
        )

    def process_whatsapp_message(self, body):
        wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        message_body = message["text"]["body"]

        # AI Integration
        response_msg = process_message(message_body, wa_id, name, self.channel_id)

        data = self.get_text_message_input(wa_id, response_msg)
        if self.channel.auto_reply:
            self.send_message(data)
            logging.info(f"================= WHATSAPP MESSAGE SEND")

    def process_text_for_whatsapp(self,text):
        # Remove brackets
        pattern = r"\【.*?\】"
        # Substitute the pattern with an empty string
        text = re.sub(pattern, "", text).strip()
        # Pattern to find double asterisks including the word(s) in between
        pattern = r"\*\*(.*?)\*\*"
        # Replacement pattern with single asterisks
        replacement = r"*\1*"
        # Substitute occurrences of the pattern with the replacement
        whatsapp_style_text = re.sub(pattern, replacement, text)
        return whatsapp_style_text

    def get_text_message_input(self, recipient, text):
        return json.dumps(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "text",
                "text": {"preview_url": False, "body": text},
            }
        )


    def send_message(self, data):
        headers = {
            "Content-type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        url = f"https://graph.facebook.com/{self.version}/{self.phone_number_id}/messages"
        try:
            response = requests.post(
                url, data=data, headers=headers, timeout=10
            )  # 10 seconds timeout as an example
            response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        except requests.Timeout:
            logging.error("Timeout occurred while sending message")
            return  request.make_response(json.dumps({"status": "error", "message": "Request timed out"}), status=408)
        except (
            requests.RequestException
        ) as e:  # This will catch any general request exception
            logging.error(f"Request failed due to: {e}")
            return  request.make_response(json.dumps({"status": "error", "message": "Failed to send message"}), status=500)
        else:
            # Process the response as normal
            return response

    def _test_connection(self):
        """ This method is used to test connection of WhatsApp Business Account"""
        logging.info("Test connection: Verify set phone uid is available in account ")
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        response = requests.get(url=f"{DEFAULT_ENDPOINT}/{self.version}/{self.account_uid}/phone_numbers", headers=headers)
        try:
            if 'error' in response.json():
                raise UserError(self._prepare_error_response(response.json()))
        except ValueError:
            if not response.ok:
                raise UserError("Network Failure")
        data = response.json().get('data', [])
        phone_values = [phone['id'] for phone in data if 'id' in phone]
        if self.phone_number_id not in phone_values:
            raise UserError(_("Phone number Id is wrong."), 'account')
        logging.info("Test connection: check app uid and token set in account")
        uploads_session_response = requests.post(url=f"{DEFAULT_ENDPOINT}/{self.version}/{self.app_uid}/uploads", params={'access_token': self.access_token})
        upload_session_id = uploads_session_response.json().get('id')
        if not upload_session_id:
            raise UserError(*self._prepare_error_response(uploads_session_response.json()))
        return True


    def _prepare_error_response(self, response):
        """
            This method is used to prepare error response
            :return tuple[str, int]: (error_message, whatsapp_error_code | -1)
        """
        if response.get('error'):
            error = response['error']
            desc = error.get('message', '')
            desc += (' - ' + error['error_user_title']) if error.get('error_user_title') else ''
            desc += ('\n\n' + error['error_user_msg']) if error.get('error_user_msg') else ''
            code = error.get('code', 'odoo')
            return (desc if desc else _("Non-descript Error"), code)
        return (_("Something went wrong when contacting WhatsApp, please try again later. If this happens frequently, contact support."), -1)
