{
    "name": "STeSI FIX ITA - l10n_it_pos_fiscalcode",
    "version": "18.0.0.1",
    "category": "Localization/Italy",
    "summary": "Fiscalcode on POS",
    "author": "Abstract, Agile Business Group, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-italy",
    "license": "AGPL-3",
    "depends": [
        'l10n_it_pos_fiscalcode',
        'point_of_sale',
    ],
    "data": [
    ],
    'assets': {
        'point_of_sale.assets': [
            '/stesi_l10n_it_posfiscalcode_fix/static/src/js/model.js',
            # '/stesi_l10n_it_posfiscalcode_fix/static/src/js/screen.js',
            # '/l10n_it_pos_fatturapa/static/src/js/screen.js',
        ],
    },
    "qweb": [
        'static/Screens/ClientDetails.xml'
    ]
}
