import logging, base64, requests, json
from email.mime.text import MIMEText
from odoo.http import request

class GmailApi:
    def __init__(self, channel,channel_id, access_token):
        self.channel = channel
        self.channel_id = channel_id
        self.access_token = access_token
        self.version = "v1"
        self.base_url = "https://gmail.googleapis.com"

    def handle_message(self, data):
        message = data.get('message')
        encoded_data = message.get('data')
        decode_data = json.loads(base64.urlsafe_b64decode(encoded_data).decode('utf-8'))
        historyId = decode_data.get('historyId', '')
        if not historyId:
            logging.info("===================== No HistoryId Found")
            return False
        return
        request.env['ir.config_parameter'].sudo().set_param('odoo_multi_channel_crm.history_id', historyId)
        config_history_id = request.env['ir.config_parameter'].sudo().get_param('odoo_multi_channel_crm.history_id')
            
        message = self.get_message_from_historyId(config_history_id)



        logging.info(f"-----------Decode Data : {decode_data}")

    def get_message_from_historyId(self, history_id):
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
            history = data.get("history", [])

            if not history:
                logging.info("No new messages found in history.")
                return []

            return data

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Request failed: {req_err}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
        return []
        

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
            print("Subject:", subject)

            print("Snippet:", message.get('snippet'))

            parts = message['payload'].get('parts', [])
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        decoded_bytes = base64.urlsafe_b64decode(data)
                        body = decoded_bytes.decode('utf-8')
                        print("Body: ", body)
        else:
            print("Failed to retrieve message:", response.status_code, response.text)


    def send_email(self, sender, to, subject, message_text, thread_id):
        # Build the email
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        # message['subject'] = subject

        # Encode in base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Gmail API endpoint
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'raw': raw_message,
            'threadId':thread_id
        }

        # Send email
        response = requests.post(url, headers=headers, json=payload)
        print(response.status_code, response.text)
