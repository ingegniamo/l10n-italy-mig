# Copyright 2019 Lorenzo Battistini
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "ITA - POS - Codice fiscale",
    "summary": "Gestione codice fiscale del cliente all'interno "
    "dell'interfaccia del POS",
    "version": "17.0.0.1",
    "development_status": "Beta",
    "category": "Point Of Sale",
    "website": "https://github.com/OCA/l10n-italy",
    "author": "Odoo Community Association (OCA)",
    "maintainers": ["eLBati"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "point_of_sale",
        "l10n_it_fiscalcode",
    ],
    "assets": {
        'point_of_sale._assets_pos': [
            'l10n_it_pos_fiscalcode/static/src/**/*.xml',
            'l10n_it_pos_fiscalcode/static/src/**/*.js'
        ],
    },
}
