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

    def _setup_pec_channel(self):
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
        return channel

    def _attachment_out(self, name="IT01234567890_TEST1.xml"):
        return self.env["fatturapa.attachment.out"].create(
            {
                "name": name,
                "datas": base64.b64encode(b"<FatturaElettronica/>"),
            }
        )

    def test_send_via_pec(self):
        channel = self._setup_pec_channel()
        attachment = self._attachment_out()
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

    def _partner(self):
        return self.env["res.partner"].create(
            {"name": "Customer", "email": "customer@example.com"}
        )

    def test_chatter_notification_never_pec(self):
        """A chatter message notified by email, with the PEC address as
        author, goes out through the normal server."""
        partner = self._partner()
        author = self.env["res.partner"].create(
            {"name": "PEC author", "email": PEC_ADDRESS}
        )
        message = partner.with_context(mail_notify_force_send=False).message_post(
            body="Hello",
            author_id=author.id,
            partner_ids=partner.ids,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        mails = self.env["mail.mail"].search([("mail_message_id", "=", message.id)])
        self.assertTrue(mails)
        for mail_server_id, _alias, _smtp_from, _ids in (
            mails._split_by_mail_configuration()
        ):
            self.assertEqual(mail_server_id, self.normal_server.id)
        mails.send()
        self.assertEqual(
            message.notification_ids.mapped("notification_status"), ["sent"]
        )

    def test_chatter_message_with_pec_server_not_sent(self):
        """A chatter message posted with the PEC server fails."""
        partner = self._partner()
        message = partner.message_post(
            body="Hello",
            partner_ids=partner.ids,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            mail_server_id=self.pec_server.id,
        )
        self.assertEqual(
            message.notification_ids.mapped("notification_status"), ["exception"]
        )

    def test_template_with_pec_server_not_sent(self):
        partner = self._partner()
        template = self.env["mail.template"].create(
            {
                "name": "PEC template",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subject": "Hello",
                "body_html": "<p>Hello</p>",
                "email_from": PEC_ADDRESS,
                "email_to": "{{ object.email }}",
                "mail_server_id": self.pec_server.id,
                "auto_delete": False,
            }
        )
        mail = self.env["mail.mail"].browse(
            template.send_mail(partner.id, force_send=True)
        )
        self.assertEqual(mail.state, "exception")
        template.mail_server_id = False
        mail = self.env["mail.mail"].browse(
            template.send_mail(partner.id, force_send=True)
        )
        self.assertEqual(mail.state, "sent")

    def test_queue_never_pec(self):
        """The mail queue (cron) does not send through the PEC server."""
        pec_mail = self._mail(mail_server_id=self.pec_server.id)
        normal_mail = self._mail()
        self.env["mail.mail"].process_email_queue(ids=(pec_mail + normal_mail).ids)
        self.assertEqual(pec_mail.state, "exception")
        self.assertEqual(normal_mail.state, "sent")

    def test_send_email_refused(self):
        """Low level sending with the PEC server is refused too."""
        message = self.MailServer.build_email(
            PEC_ADDRESS, ["customer@example.com"], "Hello", "Hello"
        )
        with self.assertRaises(UserError):
            self.MailServer.send_email(message, mail_server_id=self.pec_server.id)
        self.MailServer.send_email(message, mail_server_id=self.normal_server.id)

    def test_connect_positional_refused(self):
        with self.assertRaises(UserError):
            self.MailServer.connect(
                None, None, None, None, None, None, None, None, False,
                self.pec_server.id,
            )

    def test_send_via_pec_sends_only_the_e_invoice(self):
        """The e-invoice sending does not let other emails through the PEC
        server, neither queued ones nor the ones sent after it."""
        self._setup_pec_channel()
        queued_mail = self._mail(mail_server_id=self.pec_server.id)
        self._attachment_out().send_via_pec()
        self.assertEqual(queued_mail.state, "outgoing")
        queued_mail.send()
        self.assertEqual(queued_mail.state, "exception")
        mail = self._mail()
        mail.send()
        self.assertEqual(mail.state, "sent")
        self.assertEqual(mail.mail_server_id, self.env["ir.mail_server"])

    def test_normal_server_connection_test_unchanged(self):
        with self.assertRaises(UserError) as error:
            self.normal_server.test_smtp_connection()
        self.assertNotIn("reserved", str(error.exception))
