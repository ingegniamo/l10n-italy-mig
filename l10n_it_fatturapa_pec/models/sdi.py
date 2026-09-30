# Copyright 2018 Sergio Corato (https://efatto.it)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re

from odoo import _, api, exceptions, fields, models

from odoo.addons.base.models.ir_mail_server import extract_rfc2822_addresses

_logger = logging.getLogger(__name__)

# Address of the first PEC sending, when the parameter is not set
SDI_PEC_FIRST_ADDRESS = "sdi01@pec.fatturapa.it"
# Addresses the SdI sends its PEC messages from
SDI_PEC_ADDRESS_REGEX = re.compile(r"sdi[0-9]+@pec\.fatturapa\.it", re.IGNORECASE)


class SdiChannel(models.Model):
    _inherit = "sdi.channel"

    channel_type = fields.Selection(
        selection_add=[("pec", "PEC")], ondelete={"pec": "cascade"}
    )

    # SdiChannelPEC
    pec_server_id = fields.Many2one(
        "ir.mail_server",
        string="Outgoing PEC server",
        required=False,
        domain=[("is_fatturapa_pec", "=", True)],
    )
    # This is only used in configuration, to force the user to create one
    fetch_pec_server_id = fields.Many2one(
        "fetchmail.server",
        string="Incoming PEC server",
        required=False,
        domain=[("is_fatturapa_pec", "=", True)],
    )
    email_exchange_system = fields.Char(
        "Exchange System Email Address",
        help="The first time you send a PEC to SDI, you must use the address "
        "sdi01@pec.fatturapa.it . The system, with the first response "
        "or notification, communicates the PEC address to be used for "
        "future messages",
        default=lambda self: self.env["ir.config_parameter"].get_param(
            "sdi.pec.first.address", SDI_PEC_FIRST_ADDRESS
        ),
    )
    first_invoice_sent = fields.Boolean(
        "SDI already assigned a PEC address to my company",
        help="This is set after having sent the first e-invoice to SDI",
    )

    @api.constrains("fetch_pec_server_id")
    def check_fetch_pec_server_id(self):
        for channel in self:
            domain = [("fetch_pec_server_id", "=", channel.fetch_pec_server_id.id)]
            elements = self.search(domain)
            if len(elements) > 1:
                raise exceptions.ValidationError(
                    _(
                        "The channel %(name)s with pec server %(server_name)s already exists"
                    )
                    % {
                        "name": channel.name,
                        "server_name": channel.fetch_pec_server_id.name,
                    }
                )

    @api.constrains("pec_server_id")
    def check_pec_server_id(self):
        for channel in self:
            domain = [("pec_server_id", "=", channel.pec_server_id.id)]
            elements = self.search(domain)
            if len(elements) > 1:
                raise exceptions.ValidationError(
                    _(
                        "The channel %(name)s with pec server %(server_name)s already exists"
                    )
                    % {
                        "name": channel.name,
                        "server_name": channel.pec_server_id.name,
                    }
                )

    @api.constrains("email_exchange_system")
    def check_email_validity(self):
        if self.env.context.get("skip_check_email_validity"):
            return
        for channel in self:
            if not extract_rfc2822_addresses(channel.email_exchange_system):
                raise exceptions.ValidationError(
                    _("Email %s is not valid") % channel.email_exchange_system
                )

    def _get_first_address(self):
        return self.env["ir.config_parameter"].get_param(
            "sdi.pec.first.address", SDI_PEC_FIRST_ADDRESS
        )

    def check_first_pec_sending(self, attachments_count=1):
        sdi_address = self._get_first_address()
        if not self.first_invoice_sent:
            if attachments_count > 1:
                # After the first sending the address is reset, waiting for
                # the one assigned by SdI: the others would have no recipient
                raise exceptions.UserError(
                    _(
                        "This is the first sending to the Exchange System: "
                        "send one e-invoice only. The Exchange System replies "
                        "with the PEC address to use for the next ones."
                    )
                )
            if self.email_exchange_system != sdi_address:
                raise exceptions.UserError(
                    _("This is a first sending but SDI address is different " "from %s")
                    % sdi_address
                )
        else:
            if not self.email_exchange_system:
                raise exceptions.UserError(
                    _(
                        "SDI PEC address not set. It is set automatically when "
                        "the Exchange System replies to the first sending; "
                        "otherwise, set the address indicated by SDI in the "
                        "channel."
                    )
                )

    def update_exchange_system_from_sdi(self, message):
        """After the first sending, SdI replies from the PEC address to
        use for the next ones: store it, if still waiting for it."""
        self.ensure_one()
        if not self.first_invoice_sent or self.email_exchange_system:
            return False
        first_address = self._get_first_address().lower()
        for header in ("Reply-To", "From", "Return-Path"):
            for address in SDI_PEC_ADDRESS_REGEX.findall(message.get(header) or ""):
                address = address.lower()
                if address != first_address:
                    self.email_exchange_system = address
                    _logger.info(
                        "SDI channel %s: Exchange System address set to %s",
                        self.name,
                        address,
                    )
                    return address
        return False

    def update_after_first_pec_sending(self):
        if not self.first_invoice_sent:
            self.first_invoice_sent = True
            self.with_context(
                skip_check_email_validity=True
            ).email_exchange_system = False
