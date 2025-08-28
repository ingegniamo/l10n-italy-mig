from odoo import models, fields, api


class AccountAccount(models.Model):
    _inherit = 'account.account'

    def _default_cost_type(self):
            return self.account_type == 'expense'

    def _default_revenue_type(self):
        
            return self.account_type == 'income'

    cost = fields.Boolean(string="Cost", default=_default_cost_type)
    revenue = fields.Boolean(string="Revenue", default=_default_revenue_type)

