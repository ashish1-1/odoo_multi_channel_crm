import json
import logging
import re

import openai
from google import genai
from google.genai import types

from odoo.http import request


SYSTEM_INSTRUCTION = """
You are an AI assistant. Your task is to extract structured information from a conversation.

Please respond ONLY with a **valid JSON object**. Do not include any explanation or extra text. Make sure the output is strictly in this format:

{
	"customer_type": "seller or buyer",
	"products_list": ["Product1", "Product2"],
	"customer_details": {
		"name": "seller or buyer name",
		"company_name": "Company Name",
		"email": "email@example.com",
		"isd_code": "+91",
		"phone": "1234567890",
		"address": "Full address",
		"city": "City",
        "state": "State",
        "country": "Country",
		"website_link": "www.example.com"
	},
    "message_response": "Short, user-friendly summary or reply to the message"
}
"""


class MessageClassification:

    def __init__(self, ai_model, api_key):
        self.ai_model = ai_model
        self.api_key = api_key
        self.client = False
        self.model = False
        self.create_client()

    def create_client(self):
        if self.ai_model == "gemini":
            try:
                self.client = genai.Client(
                    api_key=self.api_key,
                )
                self.model = "gemini-2.5-pro-exp-03-25"
            except Exception as e:
                logging.error(f"Failed to create client: {e}")

        elif self.ai_model == "openai":
            try:
                openai.api_key = self.api_key
                self.model = "gpt-4"
            except Exception as e:
                logging.error(f"Failed to set OpenAI API key: {e}")

        else:
            pass

    def generate_content_configration(self):
        return types.GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction=[
                types.Part.from_text(text=SYSTEM_INSTRUCTION),
            ],
        )

    def prepare_gemini_previous_conversation(self, contents):
        conversation = []

        for chat in contents:
            conversation.append(
                types.Content(
                    role=list(chat.keys())[0],
                    parts=[
                        types.Part.from_text(text=list(chat.values())[0]),
                    ],
                ),
            )

        return conversation

    def prepare_openai_previous_conversation(self, contents):
        conversation = []

        for chat in contents:
            if list(chat.keys())[0] == "user":
                conversation.append({"role": "user", "content": list(chat.values())[0]})
            elif list(chat.keys())[0] == "model":
                conversation.append({"role": "assistant", "content": list(chat.values())[0]})            

        return conversation
    
    def extract_json(self, text):
        try:
            cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logging.error(f"JSON Decode Failed: {e}")
            return {}    

    def examine_msg(self, msg, contents=[]):
        if self.client and self.model and self.ai_model == "gemini":
            try:
                generate_content_config = self.generate_content_configration()
                response = ""

                conversation = self.prepare_gemini_previous_conversation(contents)

                conversation.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=msg),
                        ],
                    ),
                )

                for chunk in self.client.models.generate_content_stream(
                    model=self.model,
                    contents=conversation,
                    config=generate_content_config,
                ):
                    if chunk != None:
                        response += chunk.text

                return json.loads(response)
            except Exception as e:
                logging.error(f"Failed to generate response: {e}")
                return {}

        elif self.ai_model == "openai":
            try:
                conversation = self.prepare_openai_previous_conversation(contents)
                messages = [
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    *conversation,
                    {"role": "user", "content": msg}
                ]
                completion = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.5,
                )
                response_text = completion['choices'][0]['message']['content']
                return self.extract_json(response_text)
                # return json.loads(response_text)
            except Exception as e:
                logging.error(f"Failed to generate OpenAI response: {e}")
                return {}

        else:
            pass


def process_message(msg, identification_code=False, name=False):
    ai_model = request.env['ir.config_parameter'].sudo().get_param('odoo_multi_channel_crm.ai_model')
    api_key = request.env['ir.config_parameter'].sudo().get_param('odoo_multi_channel_crm.api_key')

    if not ai_model or not api_key:
        logging.error(f"Complete your Ai configration")

    if identification_code:
        kyc_feed_sudo = request.env['kyc.feed'].sudo().search(
            [('identification_code', '=', identification_code)]).exists()

        if not kyc_feed_sudo:
            kyc_feed_sudo = request.env['kyc.feed'].sudo().create({
                "name": name,
                "identification_code": identification_code,
                "phone": identification_code,
                "whatsapp_msg_contents_history": []
            })

        content_list = kyc_feed_sudo.whatsapp_msg_contents_history or []
        msg_clf = MessageClassification(ai_model, api_key)
        response = msg_clf.examine_msg(msg, content_list)
        logging.info(f"=================== AI RESPONSE: {response}")
        response_msg = kyc_feed_sudo.update_kyc_feed(response, msg)

        return response_msg or msg

    return "Sorry currently out of service!"
