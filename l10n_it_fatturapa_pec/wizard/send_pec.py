from odoo import models


class SendPEC(models.TransientModel):
    _name = "wizard.fatturapa.send.pec"
    _description = "Wizard to send multiple e-invoice PEC"

    def send_pec(self):
        if self.env.context.get("active_ids"):
            attachments = self.env["fatturapa.attachment.out"].browse(
                self.env.context["active_ids"]
            )
            attachments.send_via_pec()
