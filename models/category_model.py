# -*- coding: utf-8 -*-

from odoo import models, fields

class Categ(models.Model):
    _name = 'categ.categ'
    _description = 'Categ'
    _order = 'sequence,id'

    # -----------------------------
    # Fields Declaration
    # -----------------------------

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, string="Active", copy=False)
    sub_categ_ids = fields.One2many(string='Sub Categories', comodel_name='sub.categ', inverse_name='categ_id')


class SubCateg(models.Model):
    _name = 'sub.categ'
    _description = 'Sub Categ'
    _order = 'sequence,id'

    # -----------------------------
    # Fields Declaration
    # -----------------------------

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, string="Active", copy=False)
    categ_id = fields.Many2one(string='Category', comodel_name='categ.categ')
    child_categ_ids = fields.One2many(string='Child Categories', comodel_name='child.categ', inverse_name='sub_categ_id')
    forms_ids = fields.One2many(string='Forms', comodel_name='form.form', inverse_name='sub_categ_id')


class ChildCateg(models.Model):
    _name = 'child.categ'
    _description = 'Child Categ'
    _order = 'sequence,id'

    # -----------------------------
    # Fields Declaration
    # -----------------------------

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, string="Active", copy=False)
    sub_categ_id = fields.Many2one(string='Sub Category', comodel_name='sub.categ')


class SubChildCateg(models.Model):
    _name = 'sub.child.categ'
    _description = 'Sub Child Categ'
    _order = 'sequence,id'

    # -----------------------------
    # Fields Declaration
    # -----------------------------

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, string="Active", copy=False)


class Form(models.Model):
    _name = 'form.form'
    _description = 'Form'
    _order = 'sequence,id'

    # -----------------------------
    # Fields Declaration
    # -----------------------------

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, string="Active", copy=False)
    sub_categ_id = fields.Many2one(string='Sub Category', comodel_name='sub.categ')

