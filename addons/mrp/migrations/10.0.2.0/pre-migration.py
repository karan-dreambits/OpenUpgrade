# -*- coding: utf-8 -*-
# Copyright 2017 Eficent <http://www.eficent.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade
from odoo import tools

_column_copies = {
    'mrp_production': [
        ('state', None, None)
    ],
    'stock_move': [
        ('consumed_for', None, None),
    ],
}

_column_renames = {
    'mrp_bom': [
        ('product_uom', 'product_uom_id'),
    ],
}

_table_renames = [
    ('mrp_production_workcenter_line', 'mrp_workorder'),
]

_xmlid_renames = [
    ('base.menu_mrp_config', 'mrp.menu_mrp_config'),
    ('base.menu_mrp_root', 'mrp.menu_mrp_root'),
]


def prepopulate_fields(cr):
    cr.execute(
        """
        ALTER TABLE mrp_production
        ADD COLUMN picking_type_id INTEGER
        """
    )


@openupgrade.migrate(use_env=False)
def migrate(cr, version):
    openupgrade.copy_columns(cr, _column_copies)
    openupgrade.rename_columns(cr, _column_renames)
    tools.drop_view_if_exists(cr, 'mrp_workorder')
    openupgrade.rename_tables(cr, _table_renames)
    prepopulate_fields(cr)
    openupgrade.rename_xmlids(cr, _xmlid_renames)
