from odoo import models, fields, api


class AccountAccount(models.Model):
    _inherit = 'account.account'

    def _default_cost_type(self):
        cost_type = self.env.ref('account.data_account_type_expenses')
        if self.user_type_id == cost_type:
            return True
        else:
            return False

    def _default_revenue_type(self):
        revenue = self.env.ref('account.data_account_type_revenue')
        if self.user_type_id == revenue:
            return True
        else:
            return False

    cost = fields.Boolean(string="Cost", default=_default_cost_type)
    revenue = fields.Boolean(string="Revenue", default=_default_revenue_type)

