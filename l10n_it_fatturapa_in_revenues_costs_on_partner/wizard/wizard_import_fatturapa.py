#  Copyright 2022 Simone Rubino - TAKOBI
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re
from datetime import datetime

from odoo import  models
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)




class WizardImportFatturapa(models.TransientModel):
    _inherit = "wizard.import.fatturapa"
    _description = "Import E-bill"
    # def set_invoice_line_ids(
    #     self, FatturaBody, credit_account_id, partner, wt_founds, invoice
    # ):
    #     res = super(WizardImportFatturapa,self).set_invoice_line_ids(FatturaBody, credit_account_id, partner, wt_founds, invoice)
    #     if invoice.move_type in ['out_invoice'] and invoice.partner_id.revenues_account_id:
    #         credit_account_id = invoice.partner_id.revenues_account_id.id
    #     elif invoice.move_type in ['in_invoice'] and invoice.partner_id.costs_account_id:
    #         credit_account_id = invoice.partner_id.costs_account_id.id 
        
    #     return res
    def invoiceCreate(self, fatt, fatturapa_attachment, FatturaBody, partner_id):
        res = super().invoiceCreate(fatt, fatturapa_attachment, FatturaBody, partner_id)
        move_lines_product = res.invoice_line_ids.filtered(lambda f: f.display_type in ['product'])
        account_id = False
        if res.move_type in ['out_invoice'] and res.partner_id.revenues_account_id:
            account_id =  res.partner_id.revenues_account_id.id
        elif res.move_type in ['in_invoice'] and res.partner_id.costs_account_id:
            account_id = res.partner_id.costs_account_id.id
        if account_id:
            move_lines_product.write({'account_id': account_id})
        #  for move_line in res.invoice_line_ids.filtered(lambda f: f.display_type in ['product']):
        #     if move_line.move_id.move_type in ['out_invoice'] and move_line.partner_id.revenues_account_id:
        #         move_line.account_id = move_line.partner_id.revenues_account_id
        #     elif move_line.move_id.move_type in ['in_invoice'] and move_line.partner_id.costs_account_id:
        #         move_line.account_id = move_line.partner_id.costs_account_id
        return res

 
