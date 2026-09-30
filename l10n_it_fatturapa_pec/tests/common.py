# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.tests import TransactionCase

PEC_ADDRESS = "fatture@pec.example.com"


class PecCommon(TransactionCase):
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

    def _partner(self):
        return self.env["res.partner"].create(
            {"name": "Customer", "email": "customer@example.com"}
        )
