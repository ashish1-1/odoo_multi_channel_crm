import base64
import os
import json
import logging

from google import genai
from google.genai import types

SYSTEM_INSTRUCTION = """
Response message must be user friendly and must be summarised.
There will be the normal conversation
Provide the information in json format like:
{
	"customer_type": "seller/buyer",
	"products_list": ["Desk", "Chair", "Sofa"],
	"customer_details": {
		"name": "Mitchel",
		"company_name": "Mitchel pvt. ltd.",
		"email": "mitchel@mail.com",
		"isd_code": "+91",
		"phone": "8523658952",
		"address": "Plot No., Street",
		"city": "City",
        "state": "State",
        "country": "Country",
		"website_link": "www.abc.com",
	},
    "message_response": "Response to the msg"
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
                logging.info(f"Failed to create client: {e}")

        elif self.ai_model == "openai":
            pass

        else:
            pass

    def generate_content_configration(self):
        return types.GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction=[
                types.Part.from_text(text=SYSTEM_INSTRUCTION),
            ],
        )

    def examine_msg(self, msg, contents=[]):
        if self.client and self.model and self.ai_model == "gemini":
            try:
                generate_content_config = self.generate_content_configration()
                response = ""

                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=msg),
                        ],
                    ),
                )

                for chunk in self.client.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=generate_content_config,
                ):
                    if chunk != None:
                        response += chunk.text

                return json.loads(response)
            except Exception as e:
                logging.info(f"Failed to generate response: {e}")
                return {}

        elif self.ai_model == "openai":
            pass

        else:
            pass
