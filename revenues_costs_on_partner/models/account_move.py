from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        ctx_move_type = self.env.context.get('default_move_type')
        for move in self:
            if 'partner_id' in vals:
                partner = self.env['res.partner'].browse(vals['partner_id'])
                for move_line in move.invoice_line_ids:
                    if ctx_move_type and ctx_move_type == 'in_invoice':
                        if partner and partner.costs_account_id:
                            move_line.account_id = partner.costs_account_id
                        else:
                            move_line.account_id = move_line._get_computed_account()
                    elif ctx_move_type and ctx_move_type == 'out_invoice':
                        if partner and partner.revenues_account_id:
                            move_line.account_id = partner.revenues_account_id
                        else:
                            move_line.account_id = move_line._get_computed_account()
        result = super(AccountMove, self).write(vals)
        return result


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_account_id(self):
        super()._compute_account_id()
        for move_line in self.filtered(lambda f: f.display_type in ['product']):
            if move_line.move_id.move_type in ['out_invoice'] and move_line.partner_id.revenues_account_id:
                move_line.account_id = move_line.partner_id.revenues_account_id
            elif move_line.move_id.move_type in ['in_invoice'] and move_line.partner_id.costs_account_id:
                move_line.account_id = move_line.partner_id.costs_account_id


    # @api.model
    # def default_get(self, default_fields):
    #     values = super(AccountMoveLine, self).default_get(default_fields)
    #     if 'partner_id' in values: # check for value in dict
    #         partner = self.env['res.partner'].browse(values['partner_id'])
    #
    #         journal = False
    #         if self.journal_id:
    #             journal = self.journal_id
    #         elif 'journal_id' in values:
    #             journal = self.env['account.journal'].browse(values['journal_id'])
    #
    #         ctx_move_type = self.env.context.get('default_move_type')
    #
    #         if ctx_move_type and ctx_move_type == 'in_invoice':
    #             if partner.costs_account_id:
    #                 if 'account_id' in values:
    #                     values['account_id'] = partner.costs_account_id.id
    #                 else:
    #                     values.update({
    #                         'account_id': partner.costs_account_id.id
    #                     })
    #         elif ctx_move_type and ctx_move_type == 'out_invoice':
    #             if partner.revenues_account_id:
    #                 if 'account_id' in values:
    #                     values['account_id'] = partner.revenues_account_id.id
    #                 else:
    #                     values.update({
    #                         'account_id': partner.revenues_account_id.id
    #                     })
    #     return values

    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     for line in self:
    #         if not line.product_id or line.display_type in ('line_section', 'line_note'):
    #             continue
    #
    #         # line.name = line._get_computed_name()
    #         move_type = self.env.context.get('default_move_type')
    #         if move_type == 'in_invoice' and line.partner_id.costs_account_id:
    #             line.account_id = line.partner_id.costs_account_id
    #         elif move_type == 'out_invoice' and line.partner_id.revenues_account_id:
    #             line.account_id = line.partner_id.revenues_account_id
    #         # else:
    #             # line.account_id = line._get_computed_account()
    #         taxes = line._get_computed_taxes()
    #         if taxes and line.move_id.fiscal_position_id:
    #             taxes = line.move_id.fiscal_position_id.map_tax(taxes, partner=line.partner_id)
    #         line.tax_ids = taxes
    #         line.product_uom_id = line._get_computed_uom()
    #         line.price_unit = line._get_computed_price_unit()

    # required for import with xml
    # @api.model
    # @api.model_create_multi
    # def create(self, vals):
    #     result = super(AccountMoveLine, self).create(vals)
    #     invoice = result.move_id
    #     partner = invoice.partner_id
    #     if invoice:
    #         if result in invoice.invoice_line_ids:
    #             move_type = invoice.move_type
    #             if move_type == 'in_invoice':
    #                 default_account = invoice.journal_id.default_account_id
    #                 if partner.costs_account_id and result.account_id == default_account:
    #                     # if result.account_id.cost:
    #                     result.account_id = partner.costs_account_id
    #             elif move_type == 'out_invoice':
    #                 default_account = invoice.journal_id.default_account_id
    #                 if partner.revenues_account_id and result.account_id == default_account:
    #                     result.account_id = partner.revenues_account_id
    #     return result
