import logging, base64, requests, re
from email.mime.text import MIMEText
from odoo.api import Environment
from textwrap import dedent
from .ai_msg_clasification.msg_classification import process_message


class GmailApi:    
    def __init__(self, channel,channel_id, access_token):
        self.channel = channel
        self.channel_id = channel_id
        self.access_token = access_token
        self.version = "v1"
        self.base_url = "https://gmail.googleapis.com"

    # def handle_message(self, decode_data):
    #     global DUPLICATE
    #     historyId = decode_data.get('historyId', '')
    #     emailAddress = decode_data.get('emailAddress', '')

    #     rest_history_id = request.env['ir.config_parameter'].sudo().get_param('odoo_multi_channel_crm.history_id')
    #     if not rest_history_id:
    #         logging.info("===================== No Rest HistoryId Found")
    #         return False

    #     message_info = self.get_message_from_historyId(rest_history_id)
    #     if not message_info:
    #         request.env['ir.config_parameter'].sudo().set_param('odoo_multi_channel_crm.history_id', historyId)
    #         logging.info("===================== No Message Info Found")
    #         return False
    #     message = {}
    #     if message_info.get('history'):
    #         history = message_info['history'][0]
    #         if history.get('id') in DUPLICATE:
    #             logging.info("===================== REPEAT MESSAGE")
    #             return False
    #         DUPLICATE.add(history.get('id'))

    #         if history.get('messagesAdded'):
    #             message = history['messagesAdded'][0].get('message', {})

    #     if not message:
    #         request.env['ir.config_parameter'].sudo().set_param('odoo_multi_channel_crm.history_id', historyId)
    #         logging.info("===================== No Message Found")
    #         return False

    #     if "INBOX" not in message.get('labelIds'):
    #         request.env['ir.config_parameter'].sudo().set_param('odoo_multi_channel_crm.history_id', historyId)
    #         logging.info("===================== SENT MESSAGE LABEL FOUND")
    #         return False

    #     parse_message, subject, to_email, messageId = self.get_message(message.get('id'))
    #     threadId = message.get('threadId')

    #     if parse_message and to_email:
    #         response_msg = process_message(parse_message, threadId, False, self.channel_id)
    #         send_resp = False
    #         if self.channel.auto_reply:
    #             send_resp = self.send_email(sender="me", to=to_email, subject=subject, message_text=response_msg, thread_id=threadId, messageId=messageId)
    #         else:
    #             send_resp = True
    #         if not send_resp:
    #             logging.info("===================== SEND MESSAGE ISSUE")
    #             return False
    #         DUPLICATE = set()
    #         request.env['ir.config_parameter'].sudo().set_param('odoo_multi_channel_crm.history_id', historyId)
    #         return True
    #     return False

    def handle_message(self, env: Environment, historyId, last_saved_history_id):
        if not last_saved_history_id:
            logging.info("@@@@@@ : No previous history ID found, using provided one.")
            last_saved_history_id = historyId

        message_info = self.get_message_from_historyId(env, last_saved_history_id)
        if not message_info:
            logging.info("@@@@@@ : No messages found from Gmail history.")
            return False, historyId

        latest_history_id = historyId

        for history in message_info.get('history', []):
            history_id_entry = history.get('id')
            latest_history_id = max(latest_history_id, int(history_id_entry))

            if history.get('messagesAdded', []):
                message = history['messagesAdded'][0].get('message', {})
                if not message:
                    logging.info("@@@@@@ : GMAIL No MESSAGE FOUND")
                    continue

                if "INBOX" not in message.get('labelIds'):
                    logging.info("@@@@@@ : GMAIL SENT MESSAGE LABEL FOUND")
                    continue

                parse_message, subject, to_email, messageId = self.get_message(message.get('id'))
                threadId = message.get('threadId')

                if parse_message and to_email:
                    response_msg = process_message(env, parse_message, threadId, False, self.channel_id)
                    if response_msg:
                        send_resp = self.send_email(sender="me", to=to_email, subject=subject, message_text=response_msg, thread_id=threadId, messageId=messageId)

                        if not send_resp:
                            logging.warning(f"Failed to send email reply for message: {message.get('id')}")

        return True, latest_history_id

    def get_message_from_historyId(self, env:Environment, history_id):
        url = "https://gmail.googleapis.com/gmail/v1/users/me/history"
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Content-Type': 'application/json'
        }
        params = {
            'startHistoryId': history_id,
            'labelId': 'INBOX',
            'historyTypes': 'messageAdded'
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raise HTTPError if status != 200

            data = response.json()
            history = data.get("history")

            if not history:
                logging.info("No new messages found in history.")
                return {}
            return data

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
            env['ir.config_parameter'].sudo().set_param('odoo_multi_channel_crm.history_id', history_id)
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Request failed: {req_err}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
        return {}
        

    def get_message(self, message_id):
        url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            message = response.json()
            headers_list = message['payload']['headers']
            subject = next((h['value'] for h in headers_list if h['name'] == 'Subject'), '(No Subject)')
            from_email = next((h['value'] for h in headers_list if h['name'] == 'From'), '(Unknown Sender)')
            message_id_header = next((h['value'] for h in headers_list if h['name'] == 'Message-ID'), None)
            body = ""
            parts = message['payload'].get('parts', [])
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        decoded_bytes = base64.urlsafe_b64decode(data)
                        body = decoded_bytes.decode('utf-8')
                        body = re.split(r"On .* wrote:", body)[0].strip()
            
            return [dedent(f"""
Subject : {subject}
Body    : \n{body}
Email   : {from_email}
    """).strip(), subject, from_email, message_id_header]
        else:
            print("Failed to retrieve message:", response.status_code, response.text)
            return ["", None]


    def send_email(self, sender, to, subject, message_text, thread_id, messageId):
        message = MIMEText(message_text)
        message['from'] = sender
        message['to'] = to
        if subject:
            message['subject'] = subject
        if messageId:
            message['In-Reply-To'] = messageId
            message['References'] = messageId
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'raw': raw_message,
        }
        if thread_id:
            payload['threadId'] = thread_id

        response = requests.post(url, headers=headers, json=payload)
        if response.ok:
            logging.info(f"Email sent successfully to {to}")
            return True
        logging.error(f"Failed to send email: {response.status_code}, {response.text}")
        return False
