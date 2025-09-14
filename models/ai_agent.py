from odoo import models, fields, api


SELECTION_MODELS = {
    'openai': [('gpt-3.5-turbo', "GPT-3.5 Turbo"), ('gpt-4', "GPT-4"), ('gpt-4o', "GPT-4o"), ('gpt-4.1', "GPT-4.1"), ('gpt-4.1-mini', "GPT-4.1 Mini")],
}

TEMPERATURE_MAP = {
    'analytical': 0.2,
    'balanced': 0.5,
    'creative': 0.8,
}


class AIAgent(models.Model):
    _name = 'ai.agent'
    _description = 'AI Agent'

    @api.model
    def _get_llm_model_selection(self):
        selection = []
        for available_models in SELECTION_MODELS.values():
            selection.extend(available_models)
        return selection

    @api.model
    def _get_api_key(self):
        config_param_sudo = self.env['ir.config_parameter'].sudo()
        return config_param_sudo.get_param('odoo_multi_channel_crm.api_key')

    name = fields.Char(string="Agent Name", required=True)
    system_prompt = fields.Text(string="System Prompt", help="Customize to control relevance and formatting.")
    response_style = fields.Selection(
        selection=[
            ('analytical', "Analytical"),
            ('balanced', "Balanced"),
            ('creative', "Creative"),
        ],
        string="Response Style",
        default='balanced',
        required=True,
    )

    llm_model = fields.Selection(
        selection=_get_llm_model_selection,
        string="LLM Model",
        default='gpt-4.1',
        required=True,
    )

    ai_model = fields.Selection(
        string='Ai Model',
        selection=[('gemini', 'Gemini'), ('openai', 'OpenAi')],
        default='openai'
    )

    api_key = fields.Char(string="Api Key", default=_get_api_key)
    active = fields.Boolean(string="Active", default=True)

