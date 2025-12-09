# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Res_partner_costs_revenues_account_id_rel(models.Model):
    _name = 'res_partner_costs_revenues_account_id_rel'
    _table = 'res_partner_costs_revenues_account_id_rel'
    _description = 'Res_partner_costs_revenues_account_id_rel'

    partner_id = fields.Many2one('res.partner', string="Partner", required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string="Account", required=True,
                                 domain="domain_account_id")
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    domain_account_id = fields.Char(
        compute='_compute_domain_account_id',
        string="Domain for Account",
        help="Domain for the account_id field, based on the company and type of account."
    )
    @api.depends('type')
    def _compute_domain_account_id(self):
        for record in self:
            record.domain_account_id = "[('account_type', 'in', ['expense', 'asset_receivable','asset_cash','asset_current','asset_non_current','asset_fixed','asset_prepayments',  'expense','expense_direct_cost','expense_depreciation','equity', 'liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current'])]" if record.type == 'costs' else \
                                       "[('account_type', 'in', ['income', 'income_other', 'asset_receivable','asset_cash','asset_current','asset_non_current','asset_fixed','asset_prepayments',  'expense','expense_direct_cost','expense_depreciation','equity'])]"
    type = fields.Selection([
        ('costs', 'Costs'),
        ('revenues', 'Revenues'),
    ])