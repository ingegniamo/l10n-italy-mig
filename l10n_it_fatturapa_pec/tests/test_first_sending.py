# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from email.message import EmailMessage

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import PecCommon

SDI_ADDRESS = "sdi23@pec.fatturapa.it"


@tagged("post_install", "-at_install")
class TestFirstSending(PecCommon):
    def setUp(self):
        super().setUp()
        self.channel = self._setup_pec_channel()

    def _sdi_receipt(self, file_name, sender=SDI_ADDRESS, receipt="RC"):
        """PEC message from SdI with a notification about ``file_name``.

        As delivered by PEC: the SdI address is in Reply-To and in the
        "Per conto di" name of the From."""
        message = EmailMessage()
        message["From"] = '"Per conto di: %s" <posta-certificata@pec.example.com>' % (
            sender
        )
        message["Reply-To"] = sender
        message["To"] = self.pec_server.email_from_for_fatturaPA
        message["Subject"] = "POSTA CERTIFICATA: Ricevuta di consegna %s" % file_name
        message["Message-Id"] = "<%s.%s@pec.example.com>" % (receipt, file_name)
        message.set_content("Ricevuta")
        xml = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<ns3:RicevutaConsegna xmlns:ns3='http://www.fatturapa.gov.it/sdi/messaggi/v1.0'>"
            "<IdentificativoSdI>123456</IdentificativoSdI>"
            "<NomeFile>%s</NomeFile>"
            "<DataOraRicezione>2026-09-30T10:00:00.000+02:00</DataOraRicezione>"
            "<DataOraConsegna>2026-09-30T10:01:00.000+02:00</DataOraConsegna>"
            "<MessageId>987654</MessageId>"
            "</ns3:RicevutaConsegna>" % file_name
        )
        message.add_attachment(
            xml.encode(),
            maintype="application",
            subtype="xml",
            filename="%s_%s_001.xml" % (file_name.split(".")[0], receipt),
        )
        return message.as_bytes()

    def _receive(self, raw_message):
        self.env["mail.thread"].with_context(
            fetchmail_server_id=self.channel.fetch_pec_server_id.id
        ).message_process(False, raw_message)

    def test_first_sending_one_e_invoice_only(self):
        attachments = self._attachment_out() + self._attachment_out(
            "IT01234567890_TEST2.xml"
        )
        with self.assertRaisesRegex(UserError, "send one e-invoice only"):
            attachments.send_via_pec()
        self.assertEqual(attachments.mapped("state"), ["ready", "ready"])
        self.assertFalse(self.channel.first_invoice_sent)

    def test_first_sending_flow(self):
        """First e-invoice to sdi01, SdI replies from the assigned address,
        which is stored and used for the next e-invoices."""
        first = self._attachment_out()
        first.send_via_pec()
        self.assertEqual(first.state, "sent")
        self.assertTrue(self.channel.first_invoice_sent)
        self.assertFalse(self.channel.email_exchange_system)
        first_mail = self.env["mail.mail"].search(
            [("model", "=", first._name), ("res_id", "=", first.id)]
        )
        self.assertEqual(first_mail.email_to, "sdi01@pec.fatturapa.it")

        # Waiting for the address: the next sending is blocked
        second = self._attachment_out("IT01234567890_TEST2.xml")
        with self.assertRaisesRegex(UserError, "SDI PEC address not set"):
            second.send_via_pec()

        self._receive(self._sdi_receipt(first.name))
        self.assertEqual(first.state, "validated")
        self.assertEqual(self.channel.email_exchange_system, SDI_ADDRESS)

        # Now several e-invoices can be sent together, to the SdI address
        third = self._attachment_out("IT01234567890_TEST3.xml")
        (second + third).send_via_pec()
        self.assertEqual((second + third).mapped("state"), ["sent", "sent"])
        mails = self.env["mail.mail"].search(
            [("model", "=", second._name), ("res_id", "in", (second + third).ids)]
        )
        self.assertEqual(mails.mapped("email_to"), [SDI_ADDRESS, SDI_ADDRESS])

    def test_address_not_changed_once_set(self):
        """Later SdI messages from other addresses do not change it."""
        first = self._attachment_out()
        first.send_via_pec()
        self._receive(self._sdi_receipt(first.name))
        second = self._attachment_out("IT01234567890_TEST2.xml")
        second.send_via_pec()
        self._receive(self._sdi_receipt(second.name, sender="sdi55@pec.fatturapa.it"))
        self.assertEqual(second.state, "validated")
        self.assertEqual(self.channel.email_exchange_system, SDI_ADDRESS)

    def test_notification_not_about_our_e_invoice(self):
        """Only a notification about one of our e-invoices sets the address
        (e.g. not a message about a file we did not send)."""
        self._attachment_out().send_via_pec()
        self._receive(self._sdi_receipt("IT09999999999_OTHER.xml"))
        self.assertFalse(self.channel.email_exchange_system)

    def test_reply_from_first_address_ignored(self):
        first = self._attachment_out()
        first.send_via_pec()
        self._receive(self._sdi_receipt(first.name, sender="sdi01@pec.fatturapa.it"))
        self.assertFalse(self.channel.email_exchange_system)

    def test_manual_address_kept(self):
        """An address set by hand is never overwritten."""
        first = self._attachment_out()
        first.send_via_pec()
        self.channel.email_exchange_system = "sdi40@pec.fatturapa.it"
        self._receive(self._sdi_receipt(first.name))
        self.assertEqual(self.channel.email_exchange_system, "sdi40@pec.fatturapa.it")
