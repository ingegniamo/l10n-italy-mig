odoo.define('stesi_l10n_it_posfiscalcode_fix.screens', function(require){
    'use strict';

//    const ClientListScreen = require('point_of_sale.ClientListScreen');
    const ClientListScreen = require('point_of_sale.ClientDetailsEdit');
    const Registries = require('point_of_sale.Registries');
    var { Gui } = require('point_of_sale.Gui');
    var models = require('point_of_sale.models');

    const POSSaveClientOverride = ClientListScreen =>
        class extends ClientListScreen {
            async saveChanges(event) {
                debugger;
                var fiscalcode = $('.fiscalcode').val();
                debugger;
                //let partnerId = await this.rpc({
                //model: 'res.partner',
                //method: 'create_from_ui',
                //args: [event.detail.processedChanges],
                //});
                //debugger;
                //await this.env.pos.load_new_partners();
    //            debugger;
    //            this.state.selectedClient = this.env.pos.db.get_partner_by_id(partnerId);
    //            debugger;
                this.state.detailIsShown = false;
    //            debugger;
                this.render();
    //            debugger;
            }
    };
    Registries.Component.extend(ClientListScreen, POSSaveClientOverride);
    return ClientListScreen;
});
