from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _domain_account_costs(self):
        domain = []
        cost_account_type = self.env.ref('account.data_account_type_expenses')
        if cost_account_type:
            domain = [('internal_type', '=', 'other'), ('user_type_id', '=', cost_account_type.id)]
        else:
            domain = [('internal_type', '=', 'other')]

        return domain

    def _domain_account_revenues(self):
        domain = []
        revenues_account_type = self.env.ref('account.data_account_type_revenue')
        if revenues_account_type:
            domain = [('internal_type', '=', 'other'), ('user_type_id', '=', revenues_account_type.id)]
        else:
            domain = [('internal_type', '=', 'other')]

        return domain

    costs_account_id = fields.Many2one('account.account', string="Costs Account", domain=_domain_account_costs)
    revenues_account_id = fields.Many2one('account.account', string="Revenues Account", domain=_domain_account_revenues)

