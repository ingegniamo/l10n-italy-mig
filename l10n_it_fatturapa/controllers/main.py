from odoo.http import Controller, request, route


class FatturaElettronicaController(Controller):
    @route(
        [
            "/fatturapa/preview/<attachment_id>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def pdf_preview(self, attachment_id, **data):
        IrAttachment = request.env["ir.attachment"]
        if 'cid' in data and data.get('cid'):
            IrAttachment = IrAttachment.with_company(int(data.get('cid')))
        attach = IrAttachment.browse(int(attachment_id))
        html = attach.get_fattura_elettronica_preview()
        pdf = request.env["ir.actions.report"]._run_wkhtmltopdf([html])

        pdfhttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
