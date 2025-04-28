import json
import logging
import re

import openai
from openai import OpenAI
from google import genai
from google.genai import types

from odoo.http import request


SYSTEM_INSTRUCTION = """
You are an AI assistant. Your task is to extract structured information from a conversation and respond with a well-formed JSON object.

Important Instructions:
1. Respond ONLY with a valid JSON object. Do not include any explanation, markdown, or extra text. Return the JSON object directly.
2. The following fields are REQUIRED to complete the customer's KYC:
   - name
   - company_name
   - email
   - isd_code
   - phone
   - address
   - city
   - state
   - country
   - website_link
   - products_list

   If any of these fields are missing or unclear, set their value as an empty string "" (do not write "Not Provided" or any other placeholder).
   Also, politely ask the user to provide any missing details if possible.

3. In addition to the required fields, enrich the response with the following auto-detected details:
   - "customer_language": Identify the language the customer is using.
   - "continent": Infer based on the provided country.
   - "country_language": Identify the official or primary language(s) of the given country.

4. If the user provides **partial address details**, use your knowledge to intelligently infer the rest. For example:
   - If the country is provided, try to infer the ISD code.
   - If a state or city is provided, infer the country and ISD code.
   - If a phone number is provided with a recognizable ISD code, infer the country.
   - Only infer details if they are not already provided by the user.

5. Translate all user-provided details to **English** if given in another language.

6. The "message_response" field should remain in the **same language** as the user's original message.

7. If the website link is provided and the address is not given by the customer, attempt to fetch the address details from the website. If the address is found, populate the corresponding fields (company_name, address, city, state, country), and do not ask the user for the address details.

8. Additionally, ask for more detailed information regarding the customer's products, such as:
    - Loading Port
    - Monthly Quantity
    - Current Quantity
    - Loading Weight
    - Target Price

9. Automatically determine whether the message is from a **seller** or a **buyer** based on context, product-related requests, or other clues in the message. If unclear, default to an appropriate assumption (e.g., if asking for product details, assume "buyer", if offering products, assume "seller").

10. Format the "message_response" properly to improve readability. Avoid placing the response in a single line. If the  

Output format:

{
	"customer_type": "seller or buyer",
	"products_list": Product1, Product2,
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
        "customer_language": "Language detected from user's input",
        "continent": "Continent based on country",
        "country_language": "Primary language(s) of the provided country"        
	},
    "product_details": {
        "products_list": Product1, Product2,
        "loading_port": "Port location",
        "monthly_quantity": "Qty in ton",
        "current_quantity": "Qty in ton",
        "loading_weight": "Weight in ton",
        "taregt_price": "Price as per the country currency"
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
                self.client = OpenAI(
                    api_key=self.api_key
                )
                self.model = "gpt-4.1"                
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
            text = text.strip()
            text = re.sub(r"^```(?:json)?", "", text)
            text = re.sub(r"```$", "", text)

            return json.loads(text)
        except json.JSONDecodeError:
            try:
                json_match = re.search(r'{[\s\S]*}', text)
                if json_match:
                    json_str = json_match.group(0)
                    return json.loads(json_str)
            except Exception as e:
                logging.error(f"Regex JSON parse failed: {e}")
        
        logging.error("Failed to extract valid JSON from response.")
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

        elif self.client and self.ai_model == "openai":
            try:
                conversation = self.prepare_openai_previous_conversation(contents)
                messages = [
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    *conversation,
                    {"role": "user", "content": msg}
                ]
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                response_text = completion.choices[0].message.content
                return self.extract_json(response_text)
                # return json.loads(response_text)
            except Exception as e:
                logging.error(f"Failed to generate OpenAI response: {e}")
                return {}

        else:
            pass


def process_message(msg, identification_code=False, name=False, channel_id=False):
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
                "msg_contents_history": [],
                "channel_id": channel_id
            })

        if kyc_feed_sudo.kyc_state in ["error", "done"]:
            return "We will get back to you soon"

        content_list = kyc_feed_sudo.msg_contents_history or []
        msg_clf = MessageClassification(ai_model, api_key)
        response = msg_clf.examine_msg(msg, content_list)
        logging.info(f"=================== AI RESPONSE: {response}")
        response_msg = kyc_feed_sudo.update_kyc_feed(response, msg)

        return response_msg or msg

    return "Sorry currently out of service!"
