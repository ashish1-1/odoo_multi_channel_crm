from odoo import models, fields

class GmailWebhookLog(models.Model):
    _name = "gmail.webhook.log"
    _description = "Gmail Webhook Duplication Log"

    message_id = fields.Char(required=True, index=True, unique=True)
    received_at = fields.Datetime(default=fields.Datetime.now)
