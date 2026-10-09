#  Copyright 2022 Simone Rubino - TAKOBI
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, tagged

from odoo.addons.l10n_it_account.tools.account_tools import encode_for_export


@tagged("post_install", "-at_install")
class TestFatturaOutDN(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        company = cls.env.company
        rome = cls.env.ref("base.state_it_rm")
        company.partner_id.write(
            {
                "street": "Via Milano, 1",
                "city": "Roma",
                "zip": "00100",
                "state_id": rome.id,
                "country_id": cls.env.ref("base.it").id,
                "phone": "06543534343",
            }
        )
        company.write(
            {
                "vat": "IT06363391001",
                "email": "info@yourcompany.example.com",
                "fatturapa_fiscal_position_id": cls.env.ref(
                    "l10n_it_fatturapa.fatturapa_RF01"
                ).id,
            }
        )

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test customer",
                "is_company": True,
                "vat": "IT02780790107",
                "street": "Via Roma, 2",
                "city": "Roma",
                "zip": "00100",
                "state_id": rome.id,
                "country_id": cls.env.ref("base.it").id,
                "electronic_invoice_subjected": True,
                "codice_destinatario": "0000000",
            }
        )

        cls.tax = cls.env["account.tax"].create(
            {
                "name": "22% test",
                "amount": 22,
                "type_tax_use": "sale",
                "company_id": company.id,
            }
        )
        cls.product, cls.product_2 = cls.env["product.product"].create(
            [
                {
                    "name": name,
                    "detailed_type": "product",
                    "invoice_policy": "delivery",
                    "list_price": 1,
                    "taxes_id": [(6, 0, cls.tax.ids)],
                }
                for name in ("Test product A", "Test product B")
            ]
        )
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1
        )

        # Delivery note types only come with demo data
        cls.delivery_note_outgoing_type = cls.env["stock.delivery.note.type"].create(
            {
                "name": "Test outgoing",
                "code": "outgoing",
                "sequence": 0,
                "company_id": company.id,
                "sequence_id": cls.env["ir.sequence"]
                .create(
                    {
                        "name": "Test outgoing DN",
                        "prefix": "DDT/",
                        "padding": 5,
                        "company_id": company.id,
                    }
                )
                .id,
            }
        )

    # Helpers

    def _create_so(self, products_qty):
        """Confirmed sale order with one line per (product, quantity)."""
        sales_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": qty})
                    for product, qty in products_qty
                ],
            }
        )
        sales_order.action_confirm()
        return sales_order

    def _deliver(self, picking, qty_by_product=None, date="2019-08-07"):
        """Validate the picking (whole or partial, with backorder)
        and validate the delivery note it creates."""
        for move in picking.move_ids:
            qty = move.product_uom_qty
            if qty_by_product is not None:
                qty = qty_by_product.get(move.product_id, 0)
            move.write({"quantity": qty, "picked": bool(qty)})
        picking.with_context(skip_backorder=True).button_validate()
        delivery_note = picking.delivery_note_id
        self.assertIn(delivery_note.type_id, self.delivery_note_outgoing_type)
        delivery_note.date = date
        delivery_note.action_confirm()
        return delivery_note

    def _create_so_dn(self, products_qty=None, date="2019-08-07"):
        sales_order = self._create_so(products_qty or [(self.product, 1)])
        delivery_note = self._deliver(sales_order.picking_ids, date=date)
        return sales_order, delivery_note

    def _export(self, invoices, include_transport_data=None):
        """Post the invoices and export them in one e-invoice file.

        Return the wizard and the XML root.
        """
        invoices.filtered(lambda i: i.state == "draft").action_post()
        wizard = (
            self.env["wizard.export.fatturapa"]
            .with_context(active_ids=invoices.ids, active_model="account.move")
            .create({})
        )
        if include_transport_data is not None:
            wizard.include_transport_data = include_transport_data
        res = wizard.exportFatturaPA()
        attachment = self.env["fatturapa.attachment.out"].browse(res["res_id"])
        return wizard, etree.fromstring(base64.b64decode(attachment.datas))

    def _body(self, xml, invoice):
        bodies = [
            body
            for body in xml.findall("FatturaElettronicaBody")
            if body.findtext("DatiGenerali/DatiGeneraliDocumento/Numero")
            == invoice.name
        ]
        self.assertEqual(len(bodies), 1)
        return bodies[0]

    def _check_e_invoice_lines(self, body, invoice, wizard):
        """Check the invoice lines of the XML body against the invoice
        and against the order used by DatiDDT.

        Lines are matched by Descrizione: every line of the tests has
        a distinct name, except the delivery note lines, that have the same
        name when they refer to the same delivery note.
        Return the rendered lines as {NumeroLinea: Descrizione}.
        """
        rendered = [
            (int(line.findtext("NumeroLinea")), line.findtext("Descrizione"))
            for line in body.findall("DatiBeniServizi/DettaglioLinee")
        ]
        numbers = [number for number, _descr in rendered]
        self.assertEqual(numbers, list(range(1, len(rendered) + 1)))

        # A Descrizione identifies a line, or the delivery note of a line
        names_by_dn = {}
        for line in invoice.invoice_line_ids:
            names_by_dn.setdefault(line.delivery_note_id, []).append(line.name)
        other_names = names_by_dn.pop(self.env["stock.delivery.note"], [])
        self.assertEqual(len(set(other_names)), len(other_names))
        dn_names = [set(names) for names in names_by_dn.values()]
        self.assertTrue(all(len(names) == 1 for names in dn_names))
        all_dn_names = set().union(*dn_names)
        self.assertEqual(len(all_dn_names), len(dn_names))
        self.assertFalse(all_dn_names & set(other_names))

        # The order used for RiferimentoNumeroLinea is the rendered order
        e_invoice_lines = wizard._get_e_invoice_lines(invoice)
        self.assertEqual(
            [descr for _number, descr in rendered[: len(e_invoice_lines)]],
            [encode_for_export(line.name, 1000) for line in e_invoice_lines],
        )
        return dict(rendered)

    def _check_dati_ddt(self, xml, invoice, wizard):
        """DatiDDT of the invoice: one per delivery note of the invoice,
        each one referring exactly to the XML lines
        that carry the invoice lines linked to that delivery note.

        Return the DatiDDT as {NumeroDDT: (DataDDT, [RiferimentoNumeroLinea])}.
        """
        body = self._body(xml, invoice)
        rendered = self._check_e_invoice_lines(body, invoice, wizard)

        dati_ddt = {}
        for ddt in body.findall("DatiGenerali/DatiDDT"):
            numero = ddt.findtext("NumeroDDT")
            self.assertNotIn(numero, dati_ddt)
            dati_ddt[numero] = (
                ddt.findtext("DataDDT"),
                [int(n.text) for n in ddt.findall("RiferimentoNumeroLinea")],
            )
        self.assertEqual(set(dati_ddt), set(invoice.delivery_note_ids.mapped("name")))

        for delivery_note in invoice.delivery_note_ids:
            date, refs = dati_ddt[delivery_note.name]
            self.assertEqual(date, fields.Date.to_string(delivery_note.date))
            expected = {
                encode_for_export(line.name, 1000)
                for line in invoice.invoice_line_ids
                if line.delivery_note_id == delivery_note
            }
            self.assertEqual(len(refs), len(set(refs)))
            self.assertEqual({rendered[ref] for ref in refs}, expected)
            self.assertEqual(
                sorted(refs),
                sorted(n for n, descr in rendered.items() if descr in expected),
            )
        return dati_ddt

    # Tests

    def test_01_invoice_from_sale_order(self):
        """The delivery note validated before invoicing the sale order
        is exported in DatiDDT, referring to its invoice line."""
        sales_order, delivery_note = self._create_so_dn()

        invoice = sales_order._create_invoices()
        self.assertEqual(invoice.delivery_note_ids, delivery_note)
        dn_line = invoice.invoice_line_ids.filtered("delivery_note_id")
        self.assertEqual(dn_line.display_type, "line_note")

        wizard, xml = self._export(invoice)
        self.assertEqual(wizard.include_transport_data, "dati_dn")
        dati_ddt = self._check_dati_ddt(xml, invoice, wizard)
        # The delivery note line comes before the product line
        self.assertEqual(dati_ddt, {delivery_note.name: ("2019-08-07", [1])})

    def test_02_draft_delivery_note(self):
        """A delivery note still in draft when the sale order is invoiced
        is not linked to the invoice, so no DatiDDT is exported."""
        sales_order = self._create_so([(self.product, 1)])
        sales_order.picking_ids.move_ids.write({"quantity": 1, "picked": True})
        sales_order.picking_ids.button_validate()
        delivery_note = sales_order.picking_ids.delivery_note_id
        self.assertEqual(delivery_note.state, "draft")

        invoice = sales_order._create_invoices()
        self.assertFalse(invoice.delivery_note_ids)

        wizard, xml = self._export(invoice)
        self.assertFalse(wizard.include_transport_data)
        self.assertFalse(xml.findall(".//DatiDDT"))

    def test_03_invoice_without_delivery_note(self):
        """An invoice with no delivery note exports no DatiDDT."""
        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        invoice_form.partner_id = self.partner
        with invoice_form.invoice_line_ids.new() as line:
            line.product_id = self.product
        invoice = invoice_form.save()

        wizard, xml = self._export(invoice)
        self.assertFalse(wizard.include_transport_data)
        self.assertFalse(xml.findall(".//DatiDDT"))

    def test_04_sections_and_notes(self):
        """Sections and notes added to the invoice, before, between and
        after the other lines, shift the delivery note line number."""
        sales_order, delivery_note = self._create_so_dn(
            [(self.product, 1), (self.product_2, 1)]
        )
        invoice = sales_order._create_invoices()
        lines = invoice.invoice_line_ids
        first, last = min(lines.mapped("sequence")), max(lines.mapped("sequence"))
        invoice.write(
            {
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "display_type": "line_section",
                            "name": "Top section",
                            "sequence": first - 10,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "display_type": "line_note",
                            "name": "Top note",
                            "sequence": first - 5,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "display_type": "line_section",
                            "name": "Bottom section",
                            "sequence": last + 10,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "display_type": "line_note",
                            "name": "Bottom note",
                            "sequence": last + 20,
                        },
                    ),
                ]
            }
        )

        wizard, xml = self._export(invoice)
        dati_ddt = self._check_dati_ddt(xml, invoice, wizard)
        # The invoice lines of the order have sequence 0, 1 and each delivery
        # note line the sequence of its product line - 1: top section,
        # top note, delivery note A (-1), product A (0), delivery note B (0),
        # product B (1), bottom section, bottom note
        self.assertEqual(sorted(dati_ddt[delivery_note.name][1]), [3, 5])

    def test_05_lines_reordered(self):
        """Lines moved after the invoice creation (sequence changed,
        like a drag and drop) are numbered in their new order."""
        sales_order, delivery_note = self._create_so_dn(
            [(self.product, 1), (self.product_2, 1)]
        )
        invoice = sales_order._create_invoices()
        dn_lines = invoice.invoice_line_ids.filtered("delivery_note_id")
        product_lines = invoice.invoice_line_ids - dn_lines
        # Delivery note lines at the bottom, in reverse order
        top = max(invoice.invoice_line_ids.mapped("sequence"))
        dn_lines[0].sequence = top + 20
        dn_lines[1].sequence = top + 10
        product_lines[0].sequence = 1
        product_lines[1].sequence = 2

        wizard, xml = self._export(invoice)
        dati_ddt = self._check_dati_ddt(xml, invoice, wizard)
        self.assertEqual(sorted(dati_ddt[delivery_note.name][1]), [3, 4])

    def test_06_same_sequence(self):
        """Lines with the same sequence are numbered by creation order,
        in the XML and in DatiDDT."""
        sales_order, delivery_note = self._create_so_dn(
            [(self.product, 1), (self.product_2, 1)]
        )
        invoice = sales_order._create_invoices()
        invoice.invoice_line_ids.write({"sequence": 10})
        invoice.write(
            {
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {"display_type": "line_note", "name": "Note", "sequence": 10},
                    )
                ]
            }
        )

        wizard, xml = self._export(invoice)
        dati_ddt = self._check_dati_ddt(xml, invoice, wizard)
        # Creation order: product lines, then delivery note lines, then the note
        self.assertEqual(sorted(dati_ddt[delivery_note.name][1]), [3, 4])

    def test_07_two_orders_in_one_invoice(self):
        """Two sale orders, each with its delivery note, invoiced together:
        one DatiDDT per delivery note, each referring to its own lines."""
        order_1, delivery_note_1 = self._create_so_dn(
            [(self.product, 1)], date="2019-08-07"
        )
        order_2, delivery_note_2 = self._create_so_dn(
            [(self.product_2, 1)], date="2019-08-08"
        )
        invoice = (order_1 | order_2)._create_invoices()
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.delivery_note_ids, delivery_note_1 | delivery_note_2)

        wizard, xml = self._export(invoice)
        dati_ddt = self._check_dati_ddt(xml, invoice, wizard)
        self.assertEqual(dati_ddt[delivery_note_1.name][0], "2019-08-07")
        self.assertEqual(dati_ddt[delivery_note_2.name][0], "2019-08-08")

    def test_08_partial_deliveries(self):
        """An order delivered in two pickings (backorder) has two delivery
        notes on the same order line: both are exported, each one
        referring to its own invoice line."""
        sales_order = self._create_so([(self.product, 2), (self.product_2, 1)])
        delivery_note_1 = self._deliver(
            sales_order.picking_ids,
            {self.product: 1, self.product_2: 1},
            date="2019-08-07",
        )
        backorder = sales_order.picking_ids - delivery_note_1.picking_ids
        self.assertEqual(len(backorder), 1)
        try:
            with self.env.cr.savepoint():
                delivery_note_2 = self._deliver(backorder, date="2019-08-09")
        except UserError as error:
            self.skipTest("Partial deliveries are not allowed here: %s" % error)

        invoice = sales_order._create_invoices()
        self.assertEqual(invoice.delivery_note_ids, delivery_note_1 | delivery_note_2)

        wizard, xml = self._export(invoice)
        dati_ddt = self._check_dati_ddt(xml, invoice, wizard)
        self.assertEqual(len(dati_ddt[delivery_note_1.name][1]), 2)
        self.assertEqual(len(dati_ddt[delivery_note_2.name][1]), 1)

    def test_09_more_invoices_in_one_file(self):
        """More invoices in the same XML file: each body numbers its own
        lines from 1 and refers only to its own delivery notes."""
        order_1, delivery_note_1 = self._create_so_dn([(self.product, 1)])
        order_2, delivery_note_2 = self._create_so_dn(
            [(self.product, 1), (self.product_2, 1)]
        )
        invoice_1 = order_1._create_invoices()
        invoice_2 = order_2._create_invoices()
        # The section has the same sequence as the first delivery note line:
        # the line created first comes first
        invoice_2.write(
            {
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "display_type": "line_section",
                            "name": "Second invoice section",
                            "sequence": -1,
                        },
                    )
                ]
            }
        )

        wizard, xml = self._export(invoice_1 | invoice_2)
        self.assertEqual(len(xml.findall("FatturaElettronicaBody")), 2)
        dati_ddt_1 = self._check_dati_ddt(xml, invoice_1, wizard)
        dati_ddt_2 = self._check_dati_ddt(xml, invoice_2, wizard)
        self.assertEqual(set(dati_ddt_1), {delivery_note_1.name})
        self.assertEqual(set(dati_ddt_2), {delivery_note_2.name})
        self.assertEqual(dati_ddt_1[delivery_note_1.name][1], [1])
        # Delivery note A (-1), section (-1), product A (0),
        # delivery note B (0), product B (1)
        self.assertEqual(sorted(dati_ddt_2[delivery_note_2.name][1]), [1, 4])

    def test_10_delivery_note_without_invoice_lines(self):
        """A delivery note linked to the invoice with no invoice line
        of its own is exported without RiferimentoNumeroLinea."""
        sales_order, delivery_note = self._create_so_dn()
        invoice = sales_order._create_invoices()
        invoice.invoice_line_ids.filtered("delivery_note_id").unlink()
        self.assertEqual(invoice.delivery_note_ids, delivery_note)

        wizard, xml = self._export(invoice, include_transport_data="dati_dn")
        dati_ddt = self._check_dati_ddt(xml, invoice, wizard)
        self.assertEqual(dati_ddt, {delivery_note.name: ("2019-08-07", [])})

    def test_10b_option_default_without_invoice_lines(self):
        """The option is enabled by default only when an invoice line
        is linked to a delivery note."""
        sales_order, delivery_note = self._create_so_dn()
        invoice = sales_order._create_invoices()
        invoice.invoice_line_ids.filtered("delivery_note_id").unlink()

        wizard, xml = self._export(invoice)
        self.assertFalse(wizard.include_transport_data)
        self.assertFalse(xml.findall(".//DatiDDT"))

    def test_11_option_disabled(self):
        """With the option disabled in the wizard no DatiDDT is exported,
        even if the invoice has delivery notes."""
        sales_order, delivery_note = self._create_so_dn()
        invoice = sales_order._create_invoices()

        wizard, xml = self._export(invoice, include_transport_data=False)
        self.assertTrue(invoice.delivery_note_ids)
        self.assertFalse(xml.findall(".//DatiDDT"))

    def test_12_declaration_of_intent_line(self):
        """l10n_it_fatturapa_out_di adds a line after the invoice lines
        for the declarations of intent: the numbers of the invoice lines,
        and so DatiDDT, do not change."""
        if "declaration_of_intent_ids" not in self.env["account.move"]._fields:
            self.skipTest("l10n_it_fatturapa_out_di is not installed")
        sales_order, delivery_note = self._create_so_dn(
            [(self.product, 1), (self.product_2, 1)]
        )
        invoice = sales_order._create_invoices()
        invoice.action_post()
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Test declaration",
                "valid_for_declaration_of_intent": True,
                "tax_ids": [
                    (0, 0, {"tax_src_id": self.tax.id, "tax_dest_id": self.tax.id})
                ],
            }
        )
        declaration = self.env["l10n_it_declaration_of_intent.declaration"].create(
            {
                "type": "out",
                "partner_id": self.partner.id,
                "date": "2019-01-01",
                "date_start": "2019-01-01",
                "date_end": "2019-12-31",
                "telematic_protocol": "08060120341234567-000001",
                "partner_document_number": "1",
                "partner_document_date": "2019-01-01",
                "taxes_ids": [(6, 0, self.tax.ids)],
                "limit_amount": 1000,
                "fiscal_position_id": fiscal_position.id,
            }
        )
        invoice.declaration_of_intent_ids = [(4, declaration.id)]

        wizard, xml = self._export(invoice)
        body = self._body(xml, invoice)
        lines = body.findall("DatiBeniServizi/DettaglioLinee")
        self.assertEqual(len(lines), len(invoice.invoice_line_ids) + 1)
        self.assertEqual(lines[-1].findtext("Descrizione"), "Altre lettere d'intento")
        dati_ddt = self._check_dati_ddt(xml, invoice, wizard)
        self.assertEqual(sorted(dati_ddt[delivery_note.name][1]), [1, 3])
