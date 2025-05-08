odoo.define('stesi_l10n_it_posfiscalcode_fix.models', function(require){
    "use strict";

    var models = require('point_of_sale.models');

    models.load_fields('res.partner', ['fiscalcode'])
});
