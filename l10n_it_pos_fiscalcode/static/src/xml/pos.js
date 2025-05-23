/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";

patch(PartnerDetailsEdit.prototype, {
    setup() {
        super.setup();
        const partner = this.props.partner;
        this.changes.fiscalcode = partner.fiscalcode || '';
    },

    async saveChanges() {
        if (!this.changes.fiscalcode) {
            this.changes.fiscalcode = false;
        }

        await super.saveChanges();
    },
});