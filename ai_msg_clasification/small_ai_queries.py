import logging
import json
from openai import OpenAI
from google import genai
from google.genai import types
from odoo.api import Environment


class Queries:

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
                self.model = "gemini-2.5-flash-preview-05-20"
            except Exception as e:
                logging.error(f"Failed to create client: {e}")

        elif self.ai_model == "openai":
            try:
                self.client = OpenAI(
                    api_key=self.api_key
                )
                self.model = "gpt-4-turbo"
            except Exception as e:
                logging.error(f"Failed to set OpenAI API key: {e}")

        else:
            pass

    def examine_msg(self, query, SI):
        if self.client and self.model and self.ai_model == "gemini":
            try:
                response = ""
                conversation = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=query),
                        ],
                    )
                ]

                for chunk in self.client.models.generate_content_stream(
                    model=self.model,
                    contents=conversation,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        system_instruction=[
                            types.Part.from_text(text=SI),
                        ],
                    )
                ):
                    if chunk != None:
                        response += chunk.text
                return json.loads(response)
            except Exception as e:
                logging.error(f"Failed to generate response: {e}")
                return []

        elif self.client and self.ai_model == "openai":
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SI},
                        {"role": "user", "content": query}
                    ],
                )
                response_text = completion.choices[0].message.content
                return json.loads(response_text)

            except Exception as e:
                logging.error(f"Failed to generate OpenAI response: {e}")
                return []

        else:
            pass

def process_query(env: Environment, query, SI):
    ai_model = env['ir.config_parameter'].sudo().get_param('odoo_multi_channel_crm.ai_model')
    api_key = env['ir.config_parameter'].sudo().get_param('odoo_multi_channel_crm.api_key')

    mini_queries = Queries(ai_model, api_key)
    return mini_queries.examine_msg(query, SI)
