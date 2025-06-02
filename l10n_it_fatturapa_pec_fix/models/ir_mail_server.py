# Copyright 2018 Sergio Corato (https://efatto.it)
# Copyright 2018 Lorenzo Battistini
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons.base.models.ir_mail_server import IrMailServer as IrMailServerBase

class IrMailServer(models.Model):
    _inherit = "ir.mail_server"
    
    def test_smtp_connection(self):
        IrMailServerBase.test_smtp_connection(self)
    
    def _get_test_email_addresses(self):
        email_from, email_to = super()._get_test_email_addresses()
        if self.is_fatturapa_pec:
            email_from = self.email_from_for_fatturaPA
        return email_from, email_to