from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def default_get(self, default_fields):
        values = super(AccountMoveLine, self).default_get(default_fields)
        if 'partner_id' in values: # check for value in dict
            partner = self.env['res.partner'].browse(values['partner_id'])

            journal = False
            if self.journal_id:
                journal = self.journal_id
            elif 'journal_id' in values:
                journal = self.env['account.journal'].browse(values['journal_id'])

            ctx_move_type = self.env.context.get('default_move_type')

            if ctx_move_type and ctx_move_type == 'in_invoice':
                if partner.costs_account_id:
                    if 'account_id' in values:
                        values['account_id'] = partner.costs_account_id.id
                    else:
                        values.update({
                            'account_id': partner.costs_account_id.id
                        })
            elif ctx_move_type and ctx_move_type == 'out_invoice':
                if partner.revenues_account_id:
                    if 'account_id' in values:
                        values['account_id'] = partner.revenues_account_id.id
                    else:
                        values.update({
                            'account_id': partner.revenues_account_id.id
                        })
        return values


