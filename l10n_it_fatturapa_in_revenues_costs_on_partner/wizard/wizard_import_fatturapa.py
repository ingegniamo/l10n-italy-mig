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
    def invoiceCreate(self, fatt, fatturapa_attachment, FatturaBody, partner_id):
         res = super().invoiceCreate(fatt, fatturapa_attachment, FatturaBody, partner_id)
         res.invoice_line_ids._compute_account_id()
         return res

 