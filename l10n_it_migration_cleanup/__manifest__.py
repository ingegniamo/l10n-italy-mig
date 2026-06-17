# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "ITA - Migration cleanup (orphan UI records)",
    "version": "19.0.1.1.1",
    "category": "Localization/Italy",
    "summary": "Purges orphan UI records and frees stale xmlids of legacy modules during the 17->19 migration",
    "author": "STeSI Consulting",
    "website": "https://github.com/ingegniamo/l10n-italy-mig",
    "license": "AGPL-3",
    "depends": ["base"],
    "auto_install": True,
    "pre_init_hook": "pre_init_hook",
    "installable": True,
}
