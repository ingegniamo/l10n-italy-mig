# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

PEC_ADDRESS = "fatture@pec.example.com"


@tagged("post_install", "-at_install")
class TestPecMailServer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.MailServer = cls.env["ir.mail_server"]
        cls.MailServer.search([]).unlink()
        # The PEC server is the most tempting choice: first sequence,
        # and a "from" filter matching the sender of the emails below.
        cls.pec_server = cls.MailServer.create(
            {
                "name": "PEC",
                "smtp_host": "smtp.pec.example.com",
                "sequence": 1,
                "from_filter": PEC_ADDRESS,
                "is_fatturapa_pec": True,
                "email_from_for_fatturaPA": PEC_ADDRESS,
            }
        )
        cls.normal_server = cls.MailServer.create(
            {
                "name": "Normal",
                "smtp_host": "smtp.example.com",
                "sequence": 20,
            }
        )

    def _mail(self, **values):
        return self.env["mail.mail"].create(
            dict(
                {
                    "email_from": PEC_ADDRESS,
                    "email_to": "customer@example.com",
                    "subject": "Test",
                    "body_html": "<p>Test</p>",
                },
                **values,
            )
        )

    def test_find_mail_server_never_pec(self):
        for email_from in (PEC_ADDRESS, "someone@example.com", False):
            mail_server, _smtp_from = self.MailServer._find_mail_server(email_from)
            self.assertEqual(mail_server, self.normal_server, email_from)
        mail_server, _smtp_from = self.MailServer._find_mail_server(
            PEC_ADDRESS, self.MailServer.search([])
        )
        self.assertEqual(mail_server, self.normal_server)

    def test_find_mail_server_only_pec(self):
        """Without other servers, the PEC one is not used as fallback."""
        self.normal_server.active = False
        mail_server, _smtp_from = self.MailServer._find_mail_server(PEC_ADDRESS)
        self.assertFalse(mail_server)

    def test_mail_queue_never_pec(self):
        mail = self._mail()
        (mail_server_id, _alias, _smtp_from, _ids) = next(
            mail._split_by_mail_configuration()
        )
        self.assertEqual(mail_server_id, self.normal_server.id)

    def test_connect_refused(self):
        with self.assertRaises(UserError):
            self.MailServer.connect(mail_server_id=self.pec_server.id)
        # Allowed for the e-invoice sending (no connection in test mode)
        self.MailServer.with_context(fatturapa_pec_send=True).connect(
            mail_server_id=self.pec_server.id
        )
        self.MailServer.connect(mail_server_id=self.normal_server.id)

    def test_mail_with_pec_server_not_sent(self):
        """An email with the PEC server set by hand fails instead of going
        out through the PEC."""
        mail = self._mail(mail_server_id=self.pec_server.id)
        mail.send()
        self.assertEqual(mail.state, "exception")
        mail = self._mail(mail_server_id=self.pec_server.id)
        with self.assertRaises(MailDeliveryException):
            mail.send(raise_exception=True)
        mail = self._mail(mail_server_id=False)
        mail.send()
        self.assertEqual(mail.state, "sent")

    def test_send_via_pec(self):
        fetch_server = self.env["fetchmail.server"].create(
            {
                "name": "PEC in",
                "server": "imap.pec.example.com",
                "server_type": "imap",
                "is_fatturapa_pec": True,
                "state": "done",
            }
        )
        channel = self.env["sdi.channel"].create(
            {
                "name": "SdI PEC",
                "channel_type": "pec",
                "pec_server_id": self.pec_server.id,
                "fetch_pec_server_id": fetch_server.id,
                "email_exchange_system": "sdi01@pec.fatturapa.it",
            }
        )
        self.env.company.sdi_channel_id = channel
        attachment = self.env["fatturapa.attachment.out"].create(
            {
                "name": "IT01234567890_TEST1.xml",
                "datas": base64.b64encode(b"<FatturaElettronica/>"),
            }
        )
        self.env["ir.config_parameter"].search(
            [("key", "=", "sdi.pec.first.address")]
        ).unlink()
        attachment.send_via_pec()
        self.assertEqual(attachment.state, "sent")
        self.assertTrue(channel.first_invoice_sent)
        mail = self.env["mail.mail"].search(
            [("model", "=", attachment._name), ("res_id", "=", attachment.id)]
        )
        self.assertEqual(mail.mail_server_id, self.pec_server)
        self.assertEqual(mail.state, "sent")

    def test_connection_test_pec_server(self):
        """Testing the connection of the PEC server is still allowed.

        In test mode there is no SMTP session, so the test always fails:
        it must not fail because the server is reserved to e-invoices."""
        with self.assertRaises(UserError) as error:
            self.pec_server.test_smtp_connection()
        self.assertNotIn("reserved", str(error.exception))
