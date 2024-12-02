#  Copyright 2023 Simone Rubino - Aion Tech
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

NEW_MODULE_NAME = "l10n_it_asset_management"
OLD_MODULE_NAME = "assets_management"

RENAMED_MODELS = [
    (
        "report.assets_management.report_asset_journal_xlsx",
        "report.l10n_it_asset_management.report_asset_journal_xlsx",
    ),
    (
        "report.assets_management.report_asset_previsional_xlsx",
        "report.l10n_it_asset_management.report_asset_previsional_xlsx",
    ),
]


def migrate_old_module(env):
    openupgrade.rename_models(
        env.cr,
        RENAMED_MODELS,
    )


def pre_absorb_old_module(env):
    if openupgrade.is_module_installed(env.cr, OLD_MODULE_NAME):
        openupgrade.update_module_names(
            env.cr,
            [
                (OLD_MODULE_NAME, NEW_MODULE_NAME),
            ],
            merge_modules=True,
        )
        migrate_old_module(env)
