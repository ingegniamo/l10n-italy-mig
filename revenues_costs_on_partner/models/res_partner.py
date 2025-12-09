from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _domain_account_costs(self):
        return [('account_type', 'in', ['expense', "asset_receivable",
        "asset_cash",
        "asset_current",
        "asset_non_current",
        "asset_fixed",
        "asset_prepayments",  "expense",
        "expense_direct_cost",
        "expense_depreciation","equity"])]

    def _domain_account_revenues(self):
        return [('account_type', 'in', ['income', 'income_other', "asset_receivable",
        "asset_cash",
        "asset_current",
        "asset_non_current",
        "asset_fixed",
        "asset_prepayments",  "expense",
        "expense_direct_cost",
        "expense_depreciation","equity"])]
    
    allowed_costs_account_ids = fields.One2many('account.account',compute='_compute_allowed_costs_revenues_account_ids', string="Allowed Costs Accounts")
    allowed_revenues_account_ids = fields.One2many('account.account',compute='_compute_allowed_costs_revenues_account_ids', string="Allowed Revenues Accounts")
    @api.depends('additional_revenues_account_id', 'additional_costs_account_id','costs_account_id', 'revenues_account_id')
    def _compute_allowed_costs_revenues_account_ids(self):
        for partner in self:
            partner.allowed_costs_account_ids = partner.mapped('additional_costs_account_id.account_id') | partner.mapped('costs_account_id')
            partner.allowed_revenues_account_ids = partner.mapped('additional_revenues_account_id.account_id') | partner.mapped('revenues_account_id')

    costs_account_id = fields.Many2one('account.account', string="Default cost Account", domain=_domain_account_costs, company_dependent=True)
    additional_costs_account_id = fields.One2many('res_partner_costs_revenues_account_id_rel', "partner_id",
                                                   string="Costs Account",
                                                   domain=[('type','=','costs')],context={'default_type': 'costs'})
    revenues_account_id = fields.Many2one('account.account', 
                                          string="Default  Revenues Account", 
                                          domain=_domain_account_revenues, 
                                          company_dependent=True)
    additional_revenues_account_id = fields.One2many('res_partner_costs_revenues_account_id_rel', "partner_id",
                                                      string="Revenues Accounts",
                                                   domain=[('type','=','revenues')],context={'default_type': 'revenues'})
