# -*- coding: utf-8 -*-
# © 2015 Eficent Business and IT Consulting Services S.L.
# © 2015 Serpent Consulting Services Pvt. Ltd. - Sudhir Arya
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


xmlid_renames = [
    (
        'hr_timesheet_notifications.subtype_confirm',
        'hr_timesheet_sheet.mt_timesheet_confirmed'
    ),
    (
        'hr_timesheet_notifications.subtype_done',
        'hr_timesheet_sheet.mt_timesheet_approved'
    ),
]


def prepopulate_fields(cr):

    cr.execute("""SELECT column_name
    FROM information_schema.columns
    WHERE table_name='account_analytic_line' AND
    column_name='sheet_id'""")

    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE account_analytic_line ADD COLUMN sheet_id
            integer;
            COMMENT ON COLUMN account_analytic_line.sheet_id IS
            'Sheet';
            """)
        table = 'account_analytic_line'
        column = 'sheet_id'
        cr.execute("""
            CREATE INDEX "%s_%s_index" ON "%s" ("%s")
        """ % (table, column, table, column))

    cr.execute("""
        UPDATE account_analytic_line aal
        SET sheet_id = hat.sheet_id
        FROM hr_analytic_timesheet hat
        WHERE hat.line_id = aal.id
    """)


@openupgrade.migrate()
def migrate(cr, version):
    cr.execute("""
    DROP VIEW IF EXISTS hr_timesheet_sheet_sheet_account;
    """)
    prepopulate_fields(cr)

    # Migrate from hr_timesheet_notifications 7.0
    openupgrade.rename_xmlids(cr, xmlid_renames)
    cr.execute(
        """ UPDATE ir_module_module SET state='to remove'
        WHERE NAME='hr_timesheet_notifications'
            AND state IN ('to upgrade', 'to install', 'installed', 'unknown')
        """)
