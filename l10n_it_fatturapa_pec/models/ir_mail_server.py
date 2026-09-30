# Copyright 2018 Sergio Corato (https://efatto.it)
# Copyright 2018 Lorenzo Battistini
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError

# Context key allowing a connection to an e-invoice PEC server.
# Only the e-invoice sending (and the connection test) set it.
PEC_SEND_CONTEXT_KEY = "fatturapa_pec_send"


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    is_fatturapa_pec = fields.Boolean("E-invoice PEC server")
    email_from_for_fatturaPA = fields.Char("Sender Email Address")

    def _get_test_email_from(self):
        email_from = super()._get_test_email_from()
        if self.is_fatturapa_pec:
            email_from = self.email_from_for_fatturaPA
        return email_from

    def _find_mail_server(self, email_from, mail_servers=None):
        """The e-invoice PEC servers are never chosen automatically:
        whatever their sequence and "from" filter, normal emails
        (chatter, notifications, templates) never go out through them."""
        if mail_servers is None:
            mail_servers = self.sudo().search(
                [("is_fatturapa_pec", "=", False)], order="sequence"
            )
        else:
            mail_servers = mail_servers.filtered(lambda s: not s.is_fatturapa_pec)
        return super()._find_mail_server(email_from, mail_servers=mail_servers)

    def connect(self, *args, **kwargs):
        """Refuse to connect to an e-invoice PEC server outside the e-invoice
        sending, e.g. an email with the PEC server set by hand or by a
        template: that email fails instead of going out through the PEC."""
        mail_server_id = kwargs.get("mail_server_id")
        if mail_server_id is None and len(args) > 9:
            mail_server_id = args[9]
        if mail_server_id and not self.env.context.get(PEC_SEND_CONTEXT_KEY):
            mail_server = self.sudo().browse(mail_server_id)
            if mail_server.is_fatturapa_pec:
                raise UserError(
                    _(
                        "The mail server %s is reserved to the e-invoices "
                        "sent to the Exchange System.",
                        mail_server.display_name,
                    )
                )
        return super().connect(*args, **kwargs)

    def test_smtp_connection(self):
        if any(self.mapped("is_fatturapa_pec")):
            self = self.with_context(**{PEC_SEND_CONTEXT_KEY: True})
        return super(IrMailServer, self).test_smtp_connection()
