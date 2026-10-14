# Copyright Lorenzo Carta - Innovyou
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# Reintroduced from 16.0.1.5.0: DBs coming from our 17.0 port never got
# the asset_id -> l10n_it_asset_id rename.

from openupgradelib import openupgrade

MODEL_TO_RENAMED_FIELDS = {
    "account.move": [
        ("asset_ids", "l10n_it_asset_ids"),
    ],
    "account.move.line": [
        ("asset_ids", "l10n_it_asset_ids"),
    ],
    "asset.accounting.info": [
        ("asset_id", "l10n_it_asset_id"),
    ],
    "asset.depreciation": [
        ("asset_id", "l10n_it_asset_id"),
    ],
    "asset.depreciation.line": [
        ("asset_id", "l10n_it_asset_id"),
    ],
}


@openupgrade.migrate()
def migrate(env, version):
    if not openupgrade.column_exists(env.cr, "asset_depreciation", "asset_id"):
        return
    openupgrade.rename_fields(
        env,
        [
            (model_name, model_name.replace(".", "_"), old, new)
            for model_name, field_specs in MODEL_TO_RENAMED_FIELDS.items()
            for old, new in field_specs
        ],
    )
