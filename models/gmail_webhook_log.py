from odoo import models, fields

class GmailWebhookLog(models.Model):
    _name = "gmail.webhook.log"
    _description = "Gmail Webhook Duplication Log"
    _rec_name = "message_id"

    message_id = fields.Char(string="Message ID", required=True, index=True)
    received_at = fields.Datetime(string="Receive Date", default=fields.Datetime.now)

    _sql_constraints = [
        ('unique_message_id', 'unique(message_id)', 'The message ID must be unique!')
    ]

    def unlink_gmail_webhook_log(self):
        log_data = self.search([], order="id asc", limit=30)
        if log_data:
            log_data.unlink()
