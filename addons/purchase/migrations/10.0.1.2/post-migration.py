# -*- coding: utf-8 -*-
# Copyright 2017 Eficent <http://www.eficent.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    openupgrade.load_data(
        env.cr, 'purchase', 'migrations/10.0.1.2/noupdate_changes.xml',
    )

    # date_planned was not stored in 9.0 but we may have the dates from 8.0
    # lying around somewhere. For other records recompute.
    if openupgrade.column_exists(
            env.cr, 'purchase_order', 'minimum_planned_date'):
        env.cr.execute(
            """UPDATE purchase_order
            SET date_planned = minimum_planned_date
            WHERE date_planned IS NULL""")
    to_recompute = env['purchase.order'].search(
        [('date_planned', '=', False)])
    env.add_todo(
        env['purchase.order']._fields['amount_total'], to_recompute)
    env['purchase.order'].recompute()
