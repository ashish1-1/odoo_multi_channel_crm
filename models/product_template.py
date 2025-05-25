from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_crm = fields.Boolean(string='Is Crm', default=False)
    crm_categ_id = fields.Many2one(string='Category', comodel_name='categ.categ')
    sub_categ_id = fields.Many2one(string='Sub Category', comodel_name='sub.categ')
    child_categ_id = fields.Many2one(string='Child Category', comodel_name='child.categ')
    sub_child_categ_id = fields.Many2one(string='Sub Child Category', comodel_name='sub.child.categ')
    forms_id = fields.Many2one(string='Forms', comodel_name='form.form')

    product_tag_ids = fields.Many2many(string='Product Tags', comodel_name='crm.product.tags', relation="product_temp_id")
    

class CrmProductTags(models.Model):
    _name = "crm.product.tags"
    _description = "Crm Product Tags"

    name = fields.Char(string='Name')
    color = fields.Integer(string='Color')

    product_temp_id = fields.Many2one(string='Product', comodel_name='product.template')