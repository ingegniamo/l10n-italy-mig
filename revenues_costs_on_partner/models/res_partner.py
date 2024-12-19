from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _domain_account_costs(self):
        return [('account_type', 'in', ['expense',])]

    def _domain_account_revenues(self):
        return [('account_type', 'in', ['income', 'income_other'])]

    costs_account_id = fields.Many2one('account.account', string="Costs Account", domain=_domain_account_costs, company_dependent=True)
    revenues_account_id = fields.Many2one('account.account', string="Revenues Account", domain=_domain_account_revenues, company_dependent=True)
    revenues_account_id = fields.Many2one('account.account', string="Revenues Account", domain=_domain_account_revenues, company_dependent=True)
    

