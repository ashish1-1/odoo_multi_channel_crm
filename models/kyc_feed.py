import json

from google import genai
from google.genai import types

from odoo import models, fields, api

REQUIRED_KYC_FIELDS = ["customer_type", "name", "company_name", "email", "isd_code", "phone", "address", "city", "state", "country", "website_link",]

class Feed(models.Model):
    _name = "kyc.feed"
    _inherit = ['mail.thread']
    _description = "KYC Feed Informations With Message History"

    name = fields.Char(string="Customer Name")
    company_name = fields.Char(string="Company Name")
    email = fields.Char(string="Email")
    isd_code = fields.Char(string="ISD Code")
    phone = fields.Char(string="Contact No.")
    address = fields.Char(string="Company Address")
    state = fields.Char(string="State")
    city = fields.Char(string="City")
    country = fields.Char(string="Country")
    website_link = fields.Char(string="Website Link")
    customer_type = fields.Selection(string='Customer Type',selection=[('buyer', 'Buyer'), ('seller', 'Seller')])
    
    is_kyc_complete = fields.Boolean(
        string='is_kyc_complete',
        compute='_compute_is_kyc_complete'
    )

    identification_code = fields.Char(
        string='Identification Code',
        required=True,
        index=True,
    )
    
    whatsapp_msg_contents_history = fields.Json(
        string="WhatsApp Msg Content"
    )


    @api.depends("name", "company_name", "email", "isd_code", "phone", "address", "city", "state", "country", "website_link", "customer_type")
    def _compute_is_kyc_complete(self):
        for record in self:
            if (
                record.name
                and record.company_name
                and record.email
                and record.isd_code
                and record.phone
                and record.address
                and record.state
                and record.country
                and record.website_link
                and record.customer_type
            ):
                record.is_kyc_complete = True
            else:
                record.is_kyc_complete = False



    def update_kyc_feed(self, response, msg=False):
        response_msg = response.get("message_response")
        personal_information = response.get("customer_details", {})
        values = {}

        if self.is_kyc_complete:
            self.message_post(body=response_msg)
            values["whatsapp_msg_contents_history"] = self.update_msg_history(msg, response_msg)
            self.write(values)

            return response_msg
        
        response_msg += """\n\nYour KYC is not complete we need some personal details like: """

        if not self.customer_type and not response.get("customer_type", False):
            response_msg += "Buyer or Seller, "
        elif not self.customer_type and response.get("customer_type", False):
            values["customer_type"] = response.get("customer_type")
        else:
            pass

        for field in REQUIRED_KYC_FIELDS[1::]:
            if not self[field] and not personal_information.get(field, False):
                response_msg += self._fields[field].string + ", "
            elif not self[field] and personal_information.get(field, False):
                values[field] = personal_information.get(field)
            else:
                pass

        self.message_post(body=response_msg)
        values["whatsapp_msg_contents_history"] = self.update_msg_history(msg, response_msg)
        self.write(values)
        
        return response_msg

    def update_msg_history(self, msg, response_msg):
        content_list = self.whatsapp_msg_contents_history or []

        content_list += [
            {"user": msg},
            {"model": response_msg},
        ]

        return content_list
    
    def get_content_history_list(self):
        content_list = []
        history = self.whatsapp_msg_contents_history or []

        for chat in history:
            content_list.append(
                types.Content(
                    role=list(chat.keys())[0],
                    parts=[
                        types.Part.from_text(text=list(chat.keys())[0]),
                    ],
                ),                
            )

        return content_list