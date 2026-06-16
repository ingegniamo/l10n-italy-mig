import logging

_logger = logging.getLogger(__name__)

# OCA / legacy modules that exist in the database (installed) but have NO 19.0
# code on disk (orphans of the 17->19 migration). Their leftover UI records
# (views/actions/menus) still reference fields/models that no longer exist in
# the registry, which breaks view validation as soon as any live module touches
# the same model (e.g. res.partner). We delete those UI records early so the
# build can complete. Data COLUMNS are intentionally left untouched so the
# native-localization data migration (migration_account_18) can still read them.
# `l10n_it_fatturapa` is included on purpose: it is now a stub (no views), so its
# stale 17.x views must be removed too.
ORPHAN_MODULES = [
    "account_commission",
    "commission",
    "printer_zpl2",
    "studio_customization",
    "l10n_it_abicab",
    "l10n_it_account",
    "l10n_it_account_stamp",
    "l10n_it_account_tax_kind",
    "l10n_it_appointment_code",
    "l10n_it_ateco",
    "l10n_it_central_journal_reportlab",
    "l10n_it_declaration_of_intent",
    "l10n_it_fatturapa",
    "l10n_it_fatturapa_export_zip",
    "l10n_it_fatturapa_import_zip",
    "l10n_it_fatturapa_in",
    "l10n_it_fatturapa_in_purchase",
    "l10n_it_fatturapa_in_rc",
    "l10n_it_fatturapa_out",
    "l10n_it_fatturapa_out_di",
    "l10n_it_fatturapa_out_rc",
    "l10n_it_fatturapa_out_sp",
    "l10n_it_fatturapa_out_stamp",
    "l10n_it_fatturapa_out_wt",
    "l10n_it_fatturapa_sale",
    "l10n_it_fiscalcode",
    "l10n_it_fiscalcode_sale",
    "l10n_it_fiscal_document_type",
    "l10n_it_fiscal_payment_term",
    "l10n_it_ipa",
    "l10n_it_payment_reason",
    "l10n_it_pec",
    "l10n_it_rea",
    "l10n_it_reverse_charge",
    "l10n_it_sdi_channel",
    "l10n_it_split_payment",
    "l10n_it_vat_payability",
    "l10n_it_vat_registries",
    "l10n_it_vat_registries_split_payment",
    "l10n_it_website_portal_fatturapa",
    "l10n_it_website_portal_fiscalcode",
    "l10n_it_website_portal_ipa",
    "l10n_it_withholding_tax",
    "l10n_it_withholding_tax_payment",
    "l10n_it_withholding_tax_reason",
]

# (ir_model_data.model, physical table) of the UI records to purge.
_UI_TARGETS = [
    ("ir.ui.view", "ir_ui_view"),
    ("ir.actions.act_window", "ir_act_window"),
    ("ir.actions.server", "ir_act_server"),
    ("ir.actions.report", "ir_act_report_xml"),
    ("ir.ui.menu", "ir_ui_menu"),
]


def pre_init_hook(env):
    """Purge stale UI records owned by orphan (codeless) modules.

    Runs before the heavier business modules are (re)loaded, so their views can
    be validated without pulling in dangling references from the legacy l10n_it
    OCA stack.
    """
    cr = env.cr
    modules = tuple(ORPHAN_MODULES)
    for model, table in _UI_TARGETS:
        cr.execute(
            "DELETE FROM {table} WHERE id IN "
            "(SELECT res_id FROM ir_model_data "
            " WHERE model = %s AND module IN %s AND res_id IS NOT NULL)".format(
                table=table
            ),
            (model, modules),
        )
        removed = cr.rowcount
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = %s AND module IN %s",
            (model, modules),
        )
        _logger.info(
            "l10n_it_migration_cleanup: purged %s orphan %s record(s)", removed, model
        )

    # Odoo 19 moved security-group categories from `ir.module.category` to the
    # new `res.groups.privilege` model. Custom modules that re-declare their
    # `module_category_*` xmlid as `res.groups.privilege` collide with the stale
    # `ir.module.category` record carrying the same xmlid ("found record of a
    # different model"). Free those group-category xmlids so the new records can
    # be created. App-store categories (other naming) and core `base` records
    # are intentionally left untouched.
    cr.execute(
        "DELETE FROM ir_model_data "
        "WHERE model = 'ir.module.category' "
        "AND name LIKE 'module_category_%%' AND module != 'base'"
    )
    _logger.info(
        "l10n_it_migration_cleanup: freed %s stale group-category xmlid(s)",
        cr.rowcount,
    )
