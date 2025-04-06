{
    "name":"Odoo Multi Channel CRM",
    "version": '1.0',
    "sequence":1,
    "category": 'Other',
    "depends": ['mail'],
    "data":[
        'security/ir.model.access.csv',
        'views/multi_channel_crm_views.xml',
        'views/whatsapp_integration_views.xml',
        'views/kyc_feed.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    "pre_init_hook": "pre_init_check",
}
