# Copyright 2023 Nextev Srl
from odoo import SUPERUSER_ID, api


def post_init_hook(env):
    """
    Create DN types and their sequences after installing the module
    if they're not already exist
    """
    companies = env["res.company"].search([])
    for company in companies:
        env["stock.delivery.note.type"].create_dn_types(company)

def pre_init_hook(env):
    from openupgradelib import openupgrade

    try:
        env.cr.execute('CREATE TABLE back_stock_picking_rel AS SELECT * FROM huroos_delivery_note_stock_picking_rel')
    except Exception as e:
        _logger.warning("Tabella huroos_delivery_note_stock_picking_rel non trovata. Il backup e stato saltato: %s", e)

    _MODEL_TO_RENAMED_FIELDS = {
        "huroos.delivery.note": [
            ("ddt_type_id", "type_id"),
            ("ddt_line_ids", "line_ids"),
        ],
        "huroos.delivery.note.line": [
            ("ddt_id", "delivery_note_id"),
            ("product_uom", "product_uom_id"),
            ("quantity", "product_qty"),
            ("unit_price", "price_unit"),
        ],
        "res.partner": [
            ("default_ddt_transport_condition_id", "default_transport_condition_id"),
            ("default_ddt_goods_appearance_id", "default_goods_appearance_id"),
            ("default_ddt_transport_reason_id", "default_transport_reason_id"),
            ("default_ddt_transport_method_id", "default_transport_method_id"),
        ],
        "sale.order": [
            ("ddt_count", "delivery_note_count"),
            ("ddt_ids", "delivery_note_ids"),
            ("default_ddt_transport_condition_id", "default_transport_condition_id"),
            ("default_ddt_goods_appearance_id", "default_goods_appearance_id"),
            ("default_ddt_transport_reason_id", "default_transport_reason_id"),
            ("default_ddt_transport_method_id", "default_transport_method_id"),
        ],
        "account.move": [
            ("ddt_ids", "delivery_note_ids"),
        ],
    }

    _RENAME_FIELDS = {
        "huroos_delivery_note": [
            ("ddt_type_id", "type_id"),
        ],
        "huroos_delivery_note_line": [
            ("ddt_id", "delivery_note_id"),
            ("product_uom", "product_uom_id"),
            ("quantity", "product_qty"),
            ("unit_price", "price_unit"),
        ],
        "res_partner": [
            ("default_ddt_transport_condition_id", "default_transport_condition_id"),
            ("default_ddt_goods_appearance_id", "default_goods_appearance_id"),
            ("default_ddt_transport_reason_id", "default_transport_reason_id"),
            ("default_ddt_transport_method_id", "default_transport_method_id"),
        ],
        'account_tax_huroos_delivery_note_line_rel': [
            ('huroos_delivery_note_line_id', 'stock_delivery_note_line_id'),
        ],

        'huroos_delivery_note_stock_picking_rel': [
            ('huroos_delivery_note_id', 'stock_delivery_note_id'),
        ]
    }

    _DROP_COLUMNS = [
        # Delete fields
        ("res_partner", "default_transport_condition_id"),
        ("res_partner", "default_goods_appearance_id"),
        ("res_partner", "default_transport_reason_id"),
        ("res_partner", "default_transport_method_id"),

        ("sale_order", "default_transport_condition_id"),
        ("sale_order", "default_goods_appearance_id"),
        ("sale_order", "default_transport_reason_id"),
        ("sale_order", "default_transport_method_id"),
    ]

    _RENAME_MODELS = [
        (
            'ddt.goods.appearance', 'stock.picking.goods.appearance'
        ),
        (
            'ddt.transport.condition', 'stock.picking.transport.condition'
        ),
        (
            'ddt.transport.method', 'stock.picking.transport.method'
        ),
        (
            'ddt.transport.reason', 'stock.picking.transport.reason'
        ),
        (
            'huroos.ddt.type', 'stock.delivery.note.type'
        ),
        (
            'huroos.delivery.note.line', 'stock.delivery.note.line'
        ),
        (
            'huroos.delivery.note', 'stock.delivery.note'
        )
    ]

    _RENAME_TABLES = [
        (
            'ddt_goods_appearance', 'stock_picking_goods_appearance'
        ),
        (
            'ddt_transport_condition', 'stock_picking_transport_condition'
        ),
        (
            'ddt_transport_method', 'stock_picking_transport_method'
        ),
        (
            'ddt_transport_reason', 'stock_picking_transport_reason'
        ),
        (
            'huroos_ddt_type', 'stock_delivery_note_type'
        ),
        (
            'huroos_delivery_note_line', 'stock_delivery_note_line'
        ),
        (
            'huroos_delivery_note', 'stock_delivery_note'
        ),
        (
            'account_tax_huroos_delivery_note_line_rel', 'account_tax_stock_delivery_note_line_rel'
        ),
        (
            'huroos_delivery_note_stock_picking_rel', 'stock_delivery_note_stock_picking_rel'
        )
    ]

    # view_account_config_settings_ftpa_in to prevent issue due to missing arrotondamenti_generali_tax_id field
    _VIEW_TO_DEACTIVATE = [3445, 1818, 1816, 1817, ]
    env['ir.ui.view'].search([('id', 'in', _VIEW_TO_DEACTIVATE)]).write({'active': False})

    # Delete all views
    env['ir.model.data'].search([('module', '=', 'huroos_ddt'), ('model', '=', 'ir.ui.view')]).unlink()

    #openupgrade.drop_columns(env.cr, _DROP_COLUMNS)
    openupgrade.rename_columns(env.cr, _RENAME_FIELDS)
    openupgrade.rename_fields(
        env,
        [
            (
                model_name,
                model_name.replace(".", "_"),
                field_spec[0],
                field_spec[1],
            )
            for model_name, field_specs in _MODEL_TO_RENAMED_FIELDS.items()
            for field_spec in field_specs
        ],
    )
    openupgrade.rename_tables(env.cr, _RENAME_TABLES)
    openupgrade.rename_models(env.cr, _RENAME_MODELS)
