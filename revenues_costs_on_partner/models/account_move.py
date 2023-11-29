from odoo import models, fields, api



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_account_id(self):
        super()._compute_account_id()
        for move_line in self.filtered(lambda f: f.display_type in ['product']):
            if move_line.move_id.move_type in ['out_invoice'] and move_line.partner_id.revenues_account_id:
                move_line.account_id = move_line.partner_id.revenues_account_id
            elif move_line.move_id.move_type in ['in_invoice'] and move_line.partner_id.costs_account_id:
                move_line.account_id = move_line.partner_id.costs_account_id

