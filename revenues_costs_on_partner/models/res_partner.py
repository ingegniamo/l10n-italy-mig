from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    costs_account_id = fields.Many2one('account.account', string="Costs Account")
    revenues_account_id = fields.Many2one('account.account', string="Revenues Account")

