import re, logging, json
from openai import OpenAI
from google import genai
from google.genai import types
from odoo.http import request
from .ai_system_instruction import SYSTEM_INSTRUCTION
from .small_ai_queries import process_query

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
                    temperature=0.01,
                    max_tokens=800
                )
                print(f"\n\n=========={completion = }===========\n\n")
                response_text = completion.choices[0].message.content
                return self.extract_json(response_text)
                # return json.loads(response_text)
            except Exception as e:
                logging.error(f"Failed to generate OpenAI response: {e}")
                return {}

        else:
            pass


def get_system_instructions():
    return """
        You will be provided with a message containing various pieces of information. Your task is to extract and return a single unique code based on the following priorities:

        Email: If an email address is found, return it.
        Contact Number: If a phone number is found and no email is present, return the phone number.
        Website Link: If a website link is found and neither an email nor a phone number is present, return the link.
        Company Name: If a company name is found and none of the above are present, return the name.

        Please format the output as a JSON object with the key “unique_code” and the extracted value as the string.

        Extract the unique code according to the priorities above and format your response as:
        {“unique_code”: “code”}
        """

def process_message(msg, identification_code=False, name=False, channel_id=False, limit=0):
    ai_model = request.env['ir.config_parameter'].sudo().get_param('odoo_multi_channel_crm.ai_model')
    api_key = request.env['ir.config_parameter'].sudo().get_param('odoo_multi_channel_crm.api_key')

    if not ai_model or not api_key:
        logging.error(f"Complete your Ai configration")

    if identification_code and limit < 3:
        additional_msg = ""
        postfix = ""

        channel_sudo = request.env['multi.channel.crm'].sudo().browse(channel_id).exists()
        channel_name = f"Channel Name: {dict(channel_sudo._get_channel()).get(channel_sudo.channel)}\n"

        partner_sudo = request.env['res.partner'].sudo().search(
            ['|', ('email', 'ilike', identification_code), ('crm_phone', 'ilike', identification_code)], limit=1
        ).exists()

        kyc_feed_sudo = request.env['kyc.feed'].sudo().search(
            [('identification_code', 'ilike', identification_code)], limit=1, order='id desc').exists()
        
        if kyc_feed_sudo:
            feed_identification_code = kyc_feed_sudo.identification_code.split('-')
            if len(feed_identification_code) > 1:
                identification_code = "-".join(feed_identification_code[:-1:])
                postfix = f"-{int(feed_identification_code[-1]) + 1}"
            else:
                postfix = "-1"

        if not kyc_feed_sudo and not partner_sudo:
            SI = get_system_instructions()
            response = process_query(msg, SI)
            unique_code = response.get('unique_code', False)
            if unique_code:
                partner_sudo = request.env['res.partner'].sudo().search(
                    ['|', '|', '|', '|', '|', ('crm_phone', 'ilike', unique_code), ('email', 'ilike', unique_code), ('website', 'ilike', unique_code), ('website', 'ilike', unique_code), ('phone', 'ilike', unique_code), ('mobile', 'ilike', unique_code)], limit=1
                ).exists()

                kyc_feed_sudo = request.env['kyc.feed'].sudo().search(
                    [('identification_code', 'ilike', unique_code)], limit=1, order='id desc').exists()

        if not kyc_feed_sudo or kyc_feed_sudo.kyc_state == 'done' or (
            kyc_feed_sudo.kyc_state == 'draft' and
            kyc_feed_sudo.is_kyc_complete and
            kyc_feed_sudo.products_list and
            ((kyc_feed_sudo.category.casefold() == 'plastic' and kyc_feed_sudo.forms) or kyc_feed_sudo.category.casefold() != 'plastic')
        ):
            partner_fields = ["name", "company_name", "email", "mobile", "street", "city", "state", "country", "website"]
            kyc_fields = ["name", "company_name", "email", "isd_code", "phone", "address", "city", "state", "country", "website_link", "continent", "customer_language", "country_language"]
            
            if kyc_feed_sudo:
                for field in kyc_fields:
                    additional_msg += f"\n{field} : {kyc_feed_sudo[field]}"
            
            elif partner_sudo:
                for field in partner_fields:
                    if field == 'state' and partner_sudo['state_id'].name:
                        additional_msg += f"\n{field} : {partner_sudo['state_id'].name}"
                    elif field == 'country' and partner_sudo['country_id'].name:
                        additional_msg += f"\n{field} : {partner_sudo['country_id'].name}"
                    elif partner_sudo[field]:
                        additional_msg += f"\n{field} : {partner_sudo[field]}"
                    else:
                        pass
            
            else:
                pass

            msg += additional_msg

            kyc_feed_sudo = request.env['kyc.feed'].sudo().create({
                "name": name,
                "identification_code": identification_code + postfix,
                "msg_contents_history": [],
                "channel_id": channel_id
            })

            if channel_sudo and channel_sudo.channel == 'whatsapp' and not additional_msg:
                additional_msg = f"\n\nMy name is {name}.\nmy contact number is +{identification_code}"
                msg += additional_msg

        if kyc_feed_sudo.kyc_state in ["error", "done"] or kyc_feed_sudo.user_msg_count + 1 > 6:
            return "We will get back to you soon"

        msg = channel_name + msg

        logging.info(f"=================== MSG TO AI: {msg}")    

        content_list = kyc_feed_sudo.msg_contents_history or []
        msg_clf = MessageClassification(ai_model, api_key)
        response = msg_clf.examine_msg(msg, content_list)

        # if additional_msg:
        #     msg = msg.replace(additional_msg, "")
        if channel_name:
            msg = msg.replace(channel_name, "")

        logging.info(f"=================== AI RESPONSE: {response}")
        response_msg = kyc_feed_sudo.update_kyc_feed(response, msg, identification_code=identification_code, name=name, channel_id=channel_id, limit=limit)

        return response_msg or msg

    return "Sorry currently out of service!"
