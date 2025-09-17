import re, logging, json, requests, typing
_logger = logging.getLogger(__name__)
from odoo.http import request
from .ai_system_instruction import SYSTEM_INSTRUCTION, SYSTEM_INSTRUCTION_FOR_UNIQUE_CODE, PREPROMPTS
from odoo.exceptions import UserError
from textwrap import dedent
from odoo.api import Environment
from odoo import _

class ChatMessage(typing.TypedDict):
    role: str
    content: str


class ChatGptAPIService:
    def __init__(self, ai_model, api_key=None) -> None:
        self.provider = ai_model
        base_url = None
        if self.provider == 'openai':
            base_url = "https://api.openai.com"
        elif self.provider == 'gemini':
            base_url = "https://generativelanguage.googleapis.com"

        self.base_url = base_url
        self.restrict_to_sources = True
        self.token = api_key

    def get_completion(
        self,
        messages: list[ChatMessage],
        model: str = 'gpt-4',
        store: bool | None = None,
        reasoning_effort: str | None = None,
        metadata: dict | None = None,
        frequency_penalty: float | None = None,
        logit_bias: dict | None = None,
        logprobs: bool | None = None,
        top_logprobs: int | None = None,
        max_completion_tokens: int | None = None,
        n: int | None = None,
        modalities: list[str] | None = None,
        prediction: dict | None = None,
        audio: dict | None = None,
        presence_penalty: float | None = None,
        response_format: dict | None = None,
        seed: int | None = None,
        service_tier: str | None = None,
        stop: str | list[str] | None = None,
        stream: bool | None = None,
        stream_options: dict | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        parallel_tool_calls: bool | None = None,
        user: str | None = None,
    ):
        body = {
            'model': model,
            'messages': messages
        }

        self._add_if_set(body, 'store', store)
        self._add_if_set(body, 'reasoning_effort', reasoning_effort)
        self._add_if_set(body, 'metadata', metadata)
        self._add_if_set(body, 'frequency_penalty', frequency_penalty)
        self._add_if_set(body, 'logit_bias', logit_bias)
        self._add_if_set(body, 'logprobs', logprobs)
        if logprobs:
            self._add_if_set(body, 'top_logprobs', top_logprobs)
        self._add_if_set(body, 'max_completion_tokens', max_completion_tokens)
        self._add_if_set(body, 'n', n)
        self._add_if_set(body, 'modalities', modalities)
        self._add_if_set(body, 'prediction', prediction)
        if modalities and 'audio' in modalities:
            self._add_if_set(body, 'audio', audio)
        self._add_if_set(body, 'presence_penalty', presence_penalty)
        self._add_if_set(body, 'response_format', response_format)
        self._add_if_set(body, 'seed', seed)
        self._add_if_set(body, 'service_tier', service_tier)
        self._add_if_set(body, 'stop', stop)
        self._add_if_set(body, 'stream', stream)
        if stream:
            self._add_if_set(body, 'stream_options', stream_options)
        self._add_if_set(body, 'temperature', temperature)
        self._add_if_set(body, 'top_p', top_p)
        self._add_if_set(body, 'tools', tools)
        self._add_if_set(body, 'tool_choice', tool_choice)
        self._add_if_set(body, 'parallel_tool_calls', parallel_tool_calls)
        self._add_if_set(body, 'user', user)
        return self._request(
            'post',
            '/v1/chat/completions',
            self._get_base_headers(),
            body,
        )

    def _add_if_set(self, d: dict, key: str, value):
        if value is not None:
            d[key] = value

    def _get_base_headers(self) -> dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._get_api_token()}',
        }

    def _get_api_token(self):
        if self.token:
            return self.token
            
        config_param_sudo = request.env['ir.config_parameter'].sudo()
        if self.provider == 'openai' and config_param_sudo.get_param('odoo_multi_channel_crm.api_key'):
            return config_param_sudo.get_param('odoo_multi_channel_crm.api_key')
        elif self.provider == 'gemini' and config_param_sudo.get_param('odoo_multi_channel_crm.api_keyy'):
            return config_param_sudo.get_param('odoo_multi_channel_crm.api_key')
        raise UserError(_("No API key set for provider '%s'", self.provider))

    def _request(self, method: str, endpoint: str, headers: dict[str, str], body: dict, data: dict | None = None, files: dict | None = None) -> dict:
        route = f"{self.base_url}/{endpoint.strip('/')}"
        try:
            response = requests.request(
                method,
                route,
                headers=headers,
                json=body,
                data=data,
                timeout=30,
                files=files
            )
            _logger.info(f"AI status_code @@@@@@@@@@@ : {response.status_code}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.warning("LLM API request to %s failed: %s", route, e)
            raise UserError(_("LLM API request failed: %s", e))

    def _prepare_chat_messages(self, prompt, system_prompt):
        messages = [{'role': 'system', 'content': system_prompt}]

        # context = ""

        # if self.restrict_to_sources:
        #     messages.append({
        #         'role': 'system',
        #         'content': PREPROMPTS['restrict_to_sources']
        #     })

        # if context:
        #     messages.append(
        #         {'role': 'user', 'content': f"##Context information:\n\n{context}\n{PREPROMPTS['context']}"})

        messages.append({'role': 'user', 'content': prompt})
        return messages

    def examine_msg(self, api_response):
        if self.provider == "openai":
            try:
                api_response = api_response['choices'][0]['message']
                response_text = {}
                if api_response.get('content'):
                    response_text = api_response['content']
                return self.extract_json(response_text)
            except Exception as e:
                logging.error(f"Failed to generate OpenAI response: {e}")
                return {}
        else:
            pass

    def extract_json(self, text):
        try:
            # Remove leading/trailing whitespace
            text = text.strip()

            # Remove code block markers if present
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
                text = re.sub(r"```$", "", text).strip()

            # Attempt to parse the cleaned string as JSON
            return json.loads(text)

        except json.JSONDecodeError:
            try:
                # Try to extract JSON object using regex if initial load fails
                json_match = re.search(r'\{[\s\S]*?\}', text)
                if json_match:
                    return json.loads(json_match.group(0))
            except Exception as e:
                logging.error(f"Regex JSON parse failed: {e}")

        logging.error("Failed to extract valid JSON from response.")
        return {}

def process_message(env: Environment, msg, identification_code=False, name=False, channel_id=False, limit=0):
    agent = env['ai.agent'].sudo().search([('active', '=', True)], limit=1)

    if not agent:
        logging.error(f"Complete your Ai configration")
        raise UserError(_("Provider Not Found"))

    if identification_code and limit < 3:
        additional_msg = ""
        postfix = ""

        channel_sudo = env['multi.channel.crm'].sudo().browse(channel_id).exists()
        channel_name = f"Channel Name: {dict(channel_sudo._get_channel()).get(channel_sudo.channel)}\n"

        partner_sudo = env['res.partner'].sudo().search(
            ['|', ('email', 'ilike', identification_code), ('crm_phone', 'ilike', identification_code)], limit=1
        ).exists()

        kyc_feed_sudo = env['kyc.feed'].sudo().search(
            [('identification_code', 'ilike', identification_code)], limit=1, order='id desc').exists()
        
        if kyc_feed_sudo:
            feed_identification_code = kyc_feed_sudo.identification_code.split('-')
            if len(feed_identification_code) > 1:
                identification_code = "-".join(feed_identification_code[:-1:])
                postfix = f"-{int(feed_identification_code[-1]) + 1}"
            else:
                postfix = "-1"

        if not kyc_feed_sudo and not partner_sudo:
            gptService = ChatGptAPIService(agent.ai_model, agent.api_key)
            messages = gptService._prepare_chat_messages(prompt=msg, system_prompt=SYSTEM_INSTRUCTION_FOR_UNIQUE_CODE)
            response = gptService.get_completion(
                model=agent.llm_model,
                messages=messages,
                tools=None,
                temperature=0.5,
            )
            response = gptService.examine_msg(response)
            unique_code  = ""

            if isinstance(response, dict):
                unique_code = response.get('unique_code', False)

            if unique_code:
                partner_sudo = env['res.partner'].sudo().search(
                    ['|', '|', '|', '|', '|', ('crm_phone', 'ilike', unique_code), ('email', 'ilike', unique_code), ('website', 'ilike', unique_code), ('website', 'ilike', unique_code), ('phone', 'ilike', unique_code), ('mobile', 'ilike', unique_code)], limit=1
                ).exists()

                kyc_feed_sudo = env['kyc.feed'].sudo().search(
                    [('identification_code', 'ilike', unique_code)], limit=1, order='id desc').exists()

        if not kyc_feed_sudo or kyc_feed_sudo.kyc_state == 'done' or kyc_feed_sudo.is_ready_for_lead_creation:
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
                    elif field != 'state' and partner_sudo[field]:
                        additional_msg += f"\n{field} : {partner_sudo[field]}"
                    else:
                        pass
            else:
                pass

            msg += additional_msg

            kyc_feed_sudo = env['kyc.feed'].sudo().create({
                "identification_code": identification_code + postfix,
                "channel_id": channel_id
            })

            if channel_sudo and channel_sudo.channel == 'whatsapp' and not additional_msg:
                additional_msg = f"\n\nMy name is {name}.\nmy contact number is +{identification_code}"
                msg += additional_msg

        if kyc_feed_sudo.kyc_state in ["error", "done"] or kyc_feed_sudo.user_msg_count + 1 > kyc_feed_sudo.channel_id.user_message_count_attempt:
            return "We will get back to you soon"

        msg = channel_name + msg
        gptService = ChatGptAPIService(agent.ai_model, agent.api_key)
        chat_history = kyc_feed_sudo._retrieve_chat_history() or []
        msg = chat_history + "\n"+ msg
        messages = gptService._prepare_chat_messages(prompt=msg, system_prompt=dedent(agent.system_prompt).strip())
        # full_conversation = chat_history + messages
        full_conversation = messages
        # _logger.info(full_conversation)
        api_response = gptService.get_completion(
            model=agent.llm_model,
            messages=full_conversation,
            tools=None,
            temperature=0.5,
        )
        response = gptService.examine_msg(api_response)
        # _logger.info(f"@@@@@@@@@@@@@@@@@@ : AI Response : {json.dumps(response, indent=4)}")
        if channel_name:
            msg = msg.replace(channel_name, "")

        if chat_history:
            msg = msg.replace(chat_history, "").strip()

        response_msg = kyc_feed_sudo.update_kyc_feed(response, msg, identification_code=identification_code, name=name, channel_id=channel_id, limit=limit)
        partner_record = kyc_feed_sudo.match_partner()
        if partner_record:
            if partner_record.stop_conversation:
                return False
        return response_msg or msg

    return "Sorry currently out of service!"
