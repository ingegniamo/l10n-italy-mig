from . import cli
from . import mixins
from . import models
from . import wizard

def post_init_hook(env):
    from odoo.tools import table_exists
    import logging

    _logger = logging.getLogger(__name__)

    if table_exists(env.cr, 'back_stock_picking_rel'):
        # Convert the many2many relation 1 picking multiple delivery note into a normal Many2one
        env.cr.execute("""
            UPDATE stock_picking sp
            SET delivery_note_id = rel.huroos_delivery_note_id
            FROM (
                SELECT stock_picking_id,
                       MIN(huroos_delivery_note_id) AS huroos_delivery_note_id
                FROM back_stock_picking_rel
                GROUP BY stock_picking_id
            ) rel
            WHERE sp.id = rel.stock_picking_id
        """)
        env.cr.execute("DROP TABLE back_stock_picking_rel")

        env.cr.execute("""
            SELECT ddt_id, string_agg(line_id::text, ',') as ids
              FROM ddt_rel_stock_move
             GROUP BY ddt_id
        """)

        DN = env['stock.delivery.note']
        for row in env.cr.fetchall():
            delivery_id = DN.browse(row[0])
            _logger.info('Processing Delivery Note {}'.format(delivery_id.name))
            if not delivery_id.line_ids:
                ids = [int(i) for i in row[1].split(',')]
                _logger.info('***** Adding lines {}'.format(ids))
                delivery_id._create_detail_lines(ids)
