from odoo import models, fields, api
from odoo.osv import expression
import json
import ast
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    domain_account_ids = fields.Char(compute='_compute_domain_account_ids', string='Domain Account IDs')
    @api.depends('move_id.partner_id', 'move_id.move_type', 'display_type')
    def _compute_domain_account_ids(self):
        for record in self:
            record.domain_account_ids = record._fields['account_id'].domain
            partner_id = record._origin.move_id.partner_id or record.move_id.partner_id
            if record.display_type in ['product']:
                if record.move_id.move_type in ['out_invoice'] and partner_id.allowed_revenues_account_ids:
                    record.domain_account_ids = json.dumps(expression.AND([ast.literal_eval(
                        record.domain_account_ids),
                        [('id', 'in', partner_id.allowed_revenues_account_ids.ids)]
                    ]))
                elif record.move_id.move_type in ['in_invoice'] and partner_id.allowed_costs_account_ids:
                    record.domain_account_ids = json.dumps(expression.AND([ast.literal_eval(
                        record.domain_account_ids),
                        [('id', 'in', partner_id.allowed_costs_account_ids.ids)]
                    ]))
        

    def _compute_account_id(self):
        super()._compute_account_id()
        for move_line in self.filtered(lambda f: f.display_type in ['product']):
            if move_line.move_id.move_type in ['out_invoice'] and move_line.partner_id.revenues_account_id:
                move_line.account_id = move_line.partner_id.revenues_account_id
            elif move_line.move_id.move_type in ['in_invoice'] and move_line.partner_id.costs_account_id:
                move_line.account_id = move_line.partner_id.costs_account_id

