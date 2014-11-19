# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module Copyright (C) 2012-2014 OpenUpgrade community
#    https://launchpad.net/~openupgrade-committers
#
#    Contributors:
#    Therp BV <http://therp.nl>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import xmlrpclib
import logging

try:
    from openerp.addons.openupgrade_records.lib import apriori
except ImportError:
    from openupgrade_records.lib import apriori

try:
    from openerp.osv.orm import Model, except_orm
    from openerp.osv import fields
    from openerp.tools.translate import _
except ImportError:
    from osv.osv import osv as Model, except_osv as except_orm
    from osv import fields
    from tools.translate import _


class openupgrade_comparison_config(Model):
    _name = 'openupgrade.comparison.config'
    _columns = {
        'name': fields.char('Name', size=64),
        'server': fields.char('Server', size=64, required=True),
        'port': fields.integer('Port', required=True),
        'protocol': fields.selection(
            [('http://', 'XML-RPC')],
            # ('https://', 'XML-RPC Secure')], not supported by libopenerp
            'Protocol', required=True),
        'database': fields.char('Database', size=64, required=True),
        'username': fields.char('Username', size=24, required=True),
        'password': fields.char('Password', size=24, required=True,
                                password=True),
        'last_log': fields.text('Last log'),
        }
    _defaults = {
        'port': lambda *a: 8069,
        'protocol': lambda *a: 'http://',
        }

    def get_proxy(self, cr, uid, ids, context=None):
        """ Return a lightweight XMLRPC wrapper which passes all the
        standard arguments """
        if not ids:
            raise except_orm(
                _("Cannot connect"), _("Invalid id passed."))
        conf = self.read(cr, uid, ids[0], context=None)
        host = '%(protocol)s%(server)s:%(port)s' % conf
        openerp_socket = xmlrpclib.ServerProxy(
            '%s/xmlrpc/common' % host)
        uid = openerp_socket.login(
            conf['database'], conf['username'], conf['password'])
        objects_proxy = xmlrpclib.ServerProxy(
            '%s/xmlrpc/object' % host)

        def execute(model, method, *args, **kwargs):
            return objects_proxy.execute(
                conf['database'], uid, conf['password'],
                model, method, *args, **kwargs)

        return execute

    def test_connection(self, cr, uid, ids, context=None):
        try:
            proxy = self.get_proxy(cr, uid, ids, context=context)
            user_ids = proxy(
                'res.users', 'search', [("login", "=", "admin")])
            user_info = proxy('res.users', 'read', user_ids[0], ["name"])
        except Exception, e:
            raise except_orm(
                _("Connection failed."), unicode(e))
        raise except_orm(
            _("Connection succesful."),
            _("%s is connected.") % user_info["name"]
            )

    def analyze(self, cr, uid, ids, context=None):
        """
        Run the analysis wizard
        """
        wizard_obj = self.pool.get('openupgrade.analysis.wizard')
        wizard_id = wizard_obj.create(
            cr, uid, {'server_config': ids[0]}, context)
        result = {
            'name': wizard_obj._description,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'openupgrade.analysis.wizard',
            'domain': [],
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': wizard_id,
            'nodestroy': True,
            }
        return result

    def install_modules(self, cr, uid, ids, context=None):
        """
        Install same modules as in source DB
        """
        proxy = self.get_proxy(cr, uid, [ids[0]], context)
        remote_module_ids = proxy(
            'ir.module.module', 'search', [("state", "=", "installed")])
        modules = []

        for module in proxy(
                'ir.module.module', 'read', remote_module_ids, ['name']):
            modules.append(
                apriori.renamed_modules.get(
                    module['name'], module['name']))

        _logger = logging.getLogger(__name__)
        _logger.debug('remote modules %s', modules)
        module_obj = self.pool.get('ir.module.module')
        module_ids = module_obj.search(
            cr, uid, [('name', 'in', modules),
                      ('state', '=', 'uninstalled')])
        _logger.debug('local modules %s', module_ids)
        if module_ids:
            module_obj.write(cr, uid, module_ids, {'state': 'to install'})
        return True

openupgrade_comparison_config()
