from odoo import models
from odoo.exceptions import  UserError
from odoo.tools.translate import _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def check_doc_type_relation(self):
        doc_model = self.env["fiscal.document.type"]
        for journal in self:
            docs = doc_model.search([("journal_ids", "in", [journal.id])])
            if len(docs) > 1:
                raise UserError(
                    _(
                        "Journal %(name)s can be linked to only 1 fiscal document "
                        "type (found in %(spec)s)"
                    )
                    % {"name": journal.name, "spec": ", ".join([d.code for d in docs])}
                )
