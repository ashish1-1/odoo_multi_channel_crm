# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_model = fields.Selection(
        string='Ai Model',
        selection=[('gemini', 'Gemini'), ('openai', 'OpenAi')],
        config_parameter="odoo_multi_channel_crm.ai_model"
    )

    api_key = fields.Char(
        string='Api Key',
        config_parameter="odoo_multi_channel_crm.api_key"
    )

    history_id = fields.Char(string='History Id', config_parameter='odoo_multi_channel_crm.history_id')
