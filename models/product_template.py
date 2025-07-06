from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_crm = fields.Boolean(string='Is Crm', default=True)
    crm_categ_id = fields.Many2one(string='Category', comodel_name='categ.categ')
    sub_categ_id = fields.Many2one(string='Sub Category', comodel_name='sub.categ', domain="[('categ_id', '=', crm_categ_id )]")
    child_categ_id = fields.Many2one(string='Child Category', comodel_name='child.categ' , domain="[('sub_categ_id', '=', sub_categ_id )]")
    sub_child_categ_id = fields.Many2one(string='Sub Child Category', comodel_name='sub.child.categ')
    forms_id = fields.Many2one(string='Forms', comodel_name='form.form', domain="[('sub_categ_id', '=', sub_categ_id )]")
