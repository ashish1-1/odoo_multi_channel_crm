# -*- coding: utf-8 -*-

from odoo import models, fields

class LeadType(models.Model):
    _name = 'lead.type'
    _description = 'Lead Type'
    _order = 'sequence,id'

    # -----------------------------
    # Fields Declaration
    # -----------------------------

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, string="Active", copy=False)


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

