from odoo import _, api, exceptions, fields, models
from odoo.exceptions import UserError
from odoo.addons.base.models.ir_mail_server import (
    MailDeliveryException,
    extract_rfc2822_addresses,
)

class SdiChannel(models.Model):
    _inherit = "sdi.channel"
    def send_via_pec(self, attachment_out_ids):
        self._check_fetchmail()
        self.check_first_pec_sending()
        user = self.env.user
        for att in attachment_out_ids:
            company = att.company_id
            channel_id = att.channel_id
            if not att.datas or not att.name:
                raise UserError(_("File content and file name are mandatory"))
            mail_message = self.env["mail.message"].create(
                {
                    "model": att._name,
                    "res_id": att.id,
                    "subject": att.name,
                    "body": "XML file for FatturaPA {} sent to Exchange System to "
                    "the email address {}.".format(
                        att.name, company.email_exchange_system
                    ),
                    "attachment_ids": [(6, 0, att.ir_attachment_id.ids)],
                    "email_from": (company.email_from_for_fatturaPA),
                    "reply_to": (company.email_from_for_fatturaPA),
                    "mail_server_id": channel_id.pec_server_id.id,
                }
            )

            mail = self.env["mail.mail"].create(
                {
                    "mail_message_id": mail_message.id,
                    "body_html": mail_message.body,
                    "email_to": company.email_exchange_system,
                    "headers": {"Return-Path": company.email_from_for_fatturaPA},
                }
            )

            if mail:
                try:
                    mail.send(raise_exception=True)
                    att.state = "sent"
                    att.sending_date = fields.Datetime.now()
                    att.sending_user = user.id
                    company.sdi_channel_id.update_after_first_pec_sending()
                except MailDeliveryException as e:
                    att.state = "sender_error"
                    mail.body = str(e)
