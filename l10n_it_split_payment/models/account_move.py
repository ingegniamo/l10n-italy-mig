# Copyright 2015  Davide Corio <davide.corio@abstract.it>
# Copyright 2015-2016  Lorenzo Battistini - Agile Business Group
# Copyright 2016  Alessio Gerace - Agile Business Group
# Copyright 2023  Giuseppe Borruso <gborruso@dinamicheaziendali.it>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_sp = fields.Float(
        string="Split Payment",
        digits="Account",
        store=True,
        readonly=True,
        compute="_compute_amount",
    )
    split_payment = fields.Boolean(
        string="Is Split Payment", related="fiscal_position_id.split_payment"
    )
    
    def action_post(self):
        for invoice in self.filtered(lambda l: l.split_payment):
            tax_line = invoice.line_ids.filtered(lambda l: l.display_type =='tax')[:1]
            if tax_line:
                write_off_line_vals = tax_line._build_writeoff_line()
                invoice.line_ids = [(0, 0, write_off_line_vals)]
                invoice._sync_dynamic_lines(
                    container={"records": invoice, "self": invoice}
                )
        super().action_post()
    def button_draft(self):
            # ---- Delete Collection Fees Line of invoice when set Back to Draft
            # ---- line was added on new validate
            res = super().button_draft()
            self.line_ids.with_context(check_move_validity=False, dynamic_unlink=True).filtered(lambda l: l.is_split_payment).unlink()
    def _compute_amount(self):
        res = super()._compute_amount()
        for move in self:
            if move.split_payment and move.state =='posted':
                if move.is_purchase_document():
                    continue
                if move.tax_totals:
                    move.amount_sp = (
                        move.tax_totals["amount_total"]
                        - move.tax_totals["amount_untaxed"]
                    )
                    move.amount_residual -= move.amount_tax
                    move.amount_tax = 0.0
                else:
                    move.amount_sp = 0.0
                move.amount_total = move.amount_untaxed
            else:
                move.amount_sp = 0.0
        return res
