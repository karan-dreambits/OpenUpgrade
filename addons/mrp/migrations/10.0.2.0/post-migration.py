# -*- coding: utf-8 -*-
# © 2017 Paul Catinean <https://www.pledra.com>
# Copyright 2017 Eficent <http://www.eficent.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


def migrate_bom(env):
    # Set default values from field definition as this is a new field and
    # the default val resembles the previous behavior best
    default_specs = {
        'mrp.bom': [('ready_to_produce', None)]
    }
    openupgrade.set_defaults(env.cr, env.pool, default_specs)


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    cr = env.cr
    migrate_bom(env)
    openupgrade.load_data(
        cr, 'mrp', 'migrations/10.0.2.0/noupdate_changes.xml')
