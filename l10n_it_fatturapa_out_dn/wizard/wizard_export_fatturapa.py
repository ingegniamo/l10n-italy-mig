# Copyright 2020 Marco Colommbo
# Copyright 2022 Simone Rubino - TAKOBI
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class WizardExportFatturapa(models.TransientModel):
    _inherit = "wizard.export.fatturapa"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        invoice_ids = self.env.context.get("active_ids", False)
        invoices = self.env["account.move"].browse(invoice_ids)
        # enable option by default if any invoice is connected to a dn
        if any(invoices.invoice_line_ids.mapped("delivery_note_id")):
            res["include_transport_data"] = "dati_dn"
        return res

    include_transport_data = fields.Selection(
        [
            ("dati_dn", "Include DN Data"),
        ],
        string="DN Data",
        help="Include DN data: The field must be entered when a transport "
        "document associated with a deferred invoice is present",
    )

    def _get_e_invoice_lines(self, invoice):
        """Invoice lines in the order the XML template numbers them (NumeroLinea).

        See l10n_it_fatturapa_out.account_invoice_it_fattura_elettronica_body.
        """
        return invoice.invoice_line_ids.sorted(
            key=lambda l: (-l.sequence, l.date, l.move_name, -l.id), reverse=True
        )

    def _get_dati_ddt_delivery_notes(self, invoice):
        """Delivery notes exported in DatiDDT, sorted by date.

        NumeroDDT and DataDDT are mandatory, so only delivery notes
        with a number and a date are exported.
        """
        return invoice.delivery_note_ids.filtered(
            lambda dn: dn.name and dn.date
        ).sorted(lambda dn: (dn.date, dn.id))

    def _get_dati_ddt_invoice_lines(self, invoice, delivery_note):
        """Invoice lines shipped by `delivery_note`.

        Product lines are found through the sale order lines,
        because `delivery_note_id` is only set on the note lines
        ('Delivery Note "X" of ...') added by l10n_it_delivery_note,
        and an invoice line can be shipped by more than one delivery note
        (partial deliveries): such a line belongs to all of them.
        The note lines of `delivery_note` are exported as DettaglioLinee too,
        so they are referred as well.
        """
        sale_lines = delivery_note.line_ids.sale_line_id
        return invoice.invoice_line_ids.filtered(
            lambda line: line.delivery_note_id == delivery_note
            or (line.display_type == "product" and line.sale_line_ids & sale_lines)
        )

    def getDatiDDT(self, invoice):
        """
        Get the data for rendering DatiDDT.

        RiferimentoNumeroLinea is only exported when the invoice has
        more than one delivery note: a single delivery note refers
        to the whole invoice, so its lines are not listed.

        :return: a list of dictionaries, with one dictionary per involved DdT.
        Each dictionary has shape:
        {
            '_delivery_note': <stock.delivery.note record of the involved the DdT>,

            'NumeroDDT': <string representing the DdT>,

            'DataDDT': <date of the DdT>,

            '_invoice_lines': (optional)
                <account.move.line records of invoice lines involved in the DdT>,
            'RiferimentoNumeroLinea': (optional)
                <list of the numbers of the invoice lines involved in the DdT>,
        }
        """
        self.ensure_one()
        dati_ddt_list = list()
        delivery_notes = self._get_dati_ddt_delivery_notes(invoice)
        e_invoice_lines_list = list(self._get_e_invoice_lines(invoice))
        for delivery_note in delivery_notes:
            ddt_data = {
                "_delivery_note": delivery_note,
                "NumeroDDT": delivery_note.name,
                "DataDDT": delivery_note.date,
            }
            if len(delivery_notes) > 1:
                invoice_lines = self._get_dati_ddt_invoice_lines(
                    invoice, delivery_note
                )
                if invoice_lines:
                    ddt_data.update(
                        {
                            "_invoice_lines": invoice_lines,
                            "RiferimentoNumeroLinea": sorted(
                                # NumeroLinea is 1-based
                                e_invoice_lines_list.index(line) + 1
                                for line in invoice_lines
                            ),
                        }
                    )

            dati_ddt_list.append(ddt_data)
        return dati_ddt_list
