# Copyright 2018 Sergio Corato (https://efatto.it)
# Copyright 2018 Lorenzo Battistini
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    is_fatturapa_pec = fields.Boolean("E-invoice PEC server")
    email_from_for_fatturaPA = fields.Char("Sender Email Address")

    def _get_test_email_from(self):
        email_from= super()._get_test_email_from()
        if self.is_fatturapa_pec:
            email_from = self.email_from_for_fatturaPA
        return email_from

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        access_rights_uid=None,
    ):
        if args == [] and order == "sequence" and limit == 1:
            # This happens in ir.mail_server.connect method when no SMTP server is
            # explicitly set.
            # In this case (sending normal emails without expliciting SMTP server)
            # the e-invoice PEC server must not be used
            args = [("is_fatturapa_pec", "=", False)]
        return super(IrMailServer, self)._search(
            args, offset, limit, order,  access_rights_uid
        )
