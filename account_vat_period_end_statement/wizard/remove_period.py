#  Copyright 2012 Domsense s.r.l. (<http://www.domsense.com>).
#  Copyright 2012-15 Agile Business Group sagl (<http://www.agilebg.com>)
#  Copyright 2015 Associazione Odoo Italia (<http://www.odoo-italia.org>)
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class RemovePeriod(models.TransientModel):
    _name = "remove.period.from.vat.statement"
    _description = "Remove period from VAT Statement"
    
    def _default_date_range_ids(self):
        statement = self.env["account.vat.period.end.statement"].browse(
            self.env.context["active_id"]
        )
        if not statement:
            raise UserError(_("No VAT Statement found in context."))
        return statement.date_range_ids

    period_id = fields.Many2one("date.range", "Period", required=True)
    date_range_ids = fields.Many2many("date.range", default=_default_date_range_ids)

    def remove_period(self):
        self.ensure_one()
        period = self.env["date.range"].browse(int(self.period_id.id))
        period.vat_statement_id = False
        statement = self.env["account.vat.period.end.statement"].browse(
            self.env.context["active_id"]
        )
        statement.set_fiscal_year()
        statement.compute_amounts()
        return {
            "type": "ir.actions.act_window_close",
        }
