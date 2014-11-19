# -*- coding: utf-8 -*-
# @author Stefan Rijnhart <stefan@therp.nl>
# The TinyERP 4 version of OpenUpgrade does not contain
# the necessary view definitions to generate the records
# from the database layout. Use this script instead.

import xmlrpclib

openerp_host = 'http://localhost:8069'
openerp_db = 'openupgrade'
openerp_user = 'admin'
openerp_passwd = 'admin'

openerp_socket = xmlrpclib.ServerProxy(
    '%s/xmlrpc/common' % openerp_host)
openerp_uid = openerp_socket.login(
    openerp_db, openerp_user, openerp_passwd)
objects_proxy = xmlrpclib.ServerProxy(
    '%s/xmlrpc/object' % openerp_host)


def execute(model, method, *pargs, **kwargs):
    return objects_proxy.execute(
        openerp_db, openerp_uid, openerp_passwd,
        model, method, *pargs, **kwargs)

# Install all modules
install_model = 'openupgrade.install.all.wizard'
install_id = execute(install_model, 'create', {})
execute(install_model, 'install_all', [install_id])

# Generate records
generate_model = 'openupgrade.generate.records.wizard'
generate_id = execute(generate_model, 'create', {})
execute(generate_model, 'generate', [generate_id])
