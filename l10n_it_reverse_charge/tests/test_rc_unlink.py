# Copyright 2026 STeSI Consulting
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestRCUnlink(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.account_selfinvoice = cls.env["account.account"].create(
            {
                "code": "295000",
                "name": "selfinvoice temporary",
                "account_type": "liability_current",
            }
        )
        tax_model = cls.env["account.tax"]
        cls.tax_22ai = tax_model.create(
            {
                "name": "Tax 22% Purchases Intra-EU",
                "type_tax_use": "purchase",
                "amount": 22,
            }
        )
        cls.tax_22vi = tax_model.create(
            {"name": "Tax 22% Sales Intra-EU", "type_tax_use": "sale", "amount": 22}
        )
        journal_model = cls.env["account.journal"]
        cls.journal_selfinvoice = journal_model.create(
            {
                "name": "selfinvoice",
                "type": "sale",
                "code": "SLF",
                "default_account_id": cls.account_selfinvoice.id,
            }
        )
        cls.journal_reconciliation = journal_model.create(
            {"name": "RC reconciliation", "type": "general", "code": "SLFRC"}
        )
        cls.rc_type_ieu = cls.env["account.rc.type"].create(
            {
                "name": "Intra EU (selfinvoice)",
                "method": "selfinvoice",
                "partner_type": "supplier",
                "journal_id": cls.journal_selfinvoice.id,
                "payment_journal_id": cls.journal_reconciliation.id,
                "transitory_account_id": cls.account_selfinvoice.id,
            }
        )
        cls.env["account.rc.type.tax"].create(
            {
                "rc_type_id": cls.rc_type_ieu.id,
                "purchase_tax_id": cls.tax_22ai.id,
                "sale_tax_id": cls.tax_22vi.id,
            }
        )
        cls.fiscal_position_intra = cls.env["account.fiscal.position"].create(
            {"name": "Intra EU", "rc_type_id": cls.rc_type_ieu.id}
        )
        cls.supplier_intraEU = cls.env["res.partner"].create(
            {
                "name": "Intra EU supplier",
                "property_account_position_id": cls.fiscal_position_intra.id,
            }
        )

    def test_unlink_deletes_self_invoice(self):
        invoice = self.init_invoice(
            "in_invoice",
            partner=self.supplier_intraEU,
            post=True,
            amounts=[100],
            taxes=self.tax_22ai,
        )
        self_invoice = invoice.rc_self_invoice_id
        self.assertTrue(self_invoice)

        invoice.button_draft()
        self.assertEqual(self_invoice.state, "draft")

        invoice.unlink()
        self.assertFalse(self_invoice.exists())
