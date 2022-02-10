from odoo import models, fields, api


class AccountAccount(models.Model):
    _inherit = 'account.account'

    cost = fields.Boolean(string="Cost")
    revenue = fields.Boolean(string="Revenue")

