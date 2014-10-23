##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be)
#
# $Id: __init__.py 1308 2005-09-08 18:02:01Z pinky $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contact a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os, sys, imp
import types
import itertools
from sets import Set

import osv
import tools
import pooler


import netsvc
from osv import fields

import zipfile

logger = netsvc.Logger()

### OpenUpgrade
def table_exists(cr, table):
    """ Check whether a certain table or view exists """
    cr.execute(
        'SELECT count(relname) FROM pg_class WHERE relname = %s',
        (table,))
    return cr.fetchone()[0] == 1
### End of OpenUpgrade

opj = os.path.join
ad = tools.config['addons_path']
sys.path.insert(1,ad)

class Graph(dict):

	def addNode(self, name, deps):
		max_depth, father = 0, None
		for n in [Node(x, self) for x in deps]:
			if n.depth >= max_depth:
				father = n
				max_depth = n.depth
		if father:
			father.addChild(name)
		else:
			Node(name, self)

	def __iter__(self):
		level = 0
		done = Set(self.keys())
		while done:
			level_modules = [(name, module) for name, module in self.items() if module.depth==level]
			for name, module in level_modules:
				done.remove(name)
				yield module
			level += 1

class Singleton(object):

	def __new__(cls, name, graph):
		if name in graph:
			inst = graph[name]
		else:
			inst = object.__new__(cls)
			inst.name = name
			graph[name] = inst
		return inst

class Node(Singleton):

	def __init__(self, name, graph):
		self.graph = graph
		if not hasattr(self, 'childs'):
			self.childs = []
		if not hasattr(self, 'depth'):
			self.depth = 0

	def addChild(self, name):
		node = Node(name, self.graph)
		node.depth = self.depth + 1
		if node not in self.childs:
			self.childs.append(node)
		for attr in ('init', 'update', 'demo'):
			if hasattr(self, attr):
				setattr(node, attr, True)
		self.childs.sort(lambda x,y: cmp(x.name, y.name))

	def hasChild(self, name):
		return Node(name, self.graph) in self.childs or \
				bool([c for c in self.childs if c.hasChild(name)])

	def __setattr__(self, name, value):
		super(Singleton, self).__setattr__(name, value)
		if name in ('init', 'update', 'demo'):
			tools.config[name][self.name] = 1
			for child in self.childs:
				setattr(child, name, value)
		if name == 'depth':
			for child in self.childs:
				setattr(child, name, value + 1)

	def __iter__(self):
		return itertools.chain(iter(self.childs), *map(iter, self.childs))

	def __str__(self):
		return self._pprint()

	def _pprint(self, depth=0):
		s = '%s\n' % self.name
		for c in self.childs:
			s += '%s`-> %s' % ('   ' * depth, c._pprint(depth+1))
		return s

def create_graph(module_list, force=None):
	if not force:
		force=[]
	graph = Graph()
	packages = []

	for module in module_list:
		if module[-4:]=='.zip':
			module = module[:-4]
		terp_file = opj(ad, module, '__terp__.py')
		mod_path = opj(ad, module)
		if os.path.isfile(terp_file) or zipfile.is_zipfile(mod_path+'.zip'):
			try:
				info = eval(tools.file_open(terp_file).read())
			except:
				logger.notifyChannel('init', netsvc.LOG_ERROR, 'addon:%s:eval file %s' % (module, terp_file))
				raise
			if info.get('installable', True):
				packages.append((module, info.get('depends', []), info))

	current,later = Set([p for p, dep, data in packages]), Set()
	while packages and current > later:
		package, deps, datas = packages[0]

		# if all dependencies of 'package' are already in the graph, add 'package' in the graph
		if reduce(lambda x,y: x and y in graph, deps, True):
			if not package in current:
				packages.pop(0)
				continue
			later.clear()
			current.remove(package)
			graph.addNode(package, deps)
			node = Node(package, graph)
			node.datas = datas
			for kind in ('init', 'demo', 'update'):
				if package in tools.config[kind] or 'all' in tools.config[kind] or kind in force:
					setattr(node, kind, True)
		else:
			later.add(package)
			packages.append((package, deps, datas))
		packages.pop(0)
	
	for package in later:
		logger.notifyChannel('init', netsvc.LOG_ERROR, 'addon:%s:Unmet dependency' % package)

	return graph

def init_module_objects(cr, module_name, obj_list):
	pool = pooler.get_pool(cr.dbname)
	logger.notifyChannel('init', netsvc.LOG_INFO, 'addon:%s:creating or updating database tables' % module_name)
	for obj in obj_list:
		if hasattr(obj, 'init'):
			obj.init(cr)
		obj._auto_init(cr)
		cr.commit()

def load_module_graph(cr, graph, status=None, registry=None, **kwargs):
	# **kwargs is passed directly to convert_xml_import
	if not status:
		status={}
	status = status.copy()
	package_todo = []
	statusi = 0

        import string

        local_registry = {}
        def get_repr(properties, type='val'):
                """ 
                OpenUpgrade: Return the string representation of the model or field
                for logging purposes 
                """
                if type == 'key':
                        props = ['model', 'field']
                elif type == 'val':
                        props = [
                                'type', 'isfunction', 'relation', 'required', 'selection_keys',
                                'req_default', 'inherits'
                                ]
                return ','.join([
                                '\"' + string.replace(
                                        string.replace(
                                                properties[prop], '\"', '\''), '\n','')
                                + '\"' for prop in props
                                ])

        def log_model(model):
                """                                                                                          
                OpenUpgrade: Store the characteristics of the BaseModel and its fields
                in the local registry, so that we can compare changes with the
                main registry
                """
                
                model_registry = local_registry.setdefault(
                        model._name, {})
                if model._inherits:
                        model_registry['_inherits'] = {'_inherits': unicode(model._inherits)}
                for k, v in model._columns.items():
                        properties = { 
                                'type': v._type,
                                'isfunction': (
                                        isinstance(v, osv.fields.function) and 'function' or ''),
                                'relation': (
                                        v._type in ('many2many', 'many2one','one2many')
                                        and v._obj or ''
                                        ),
                                'required': v.required and 'required' or '',
                                'selection_keys': '',
                                'req_default': '',
                                'inherits': '',
                                }
                        if v._type == 'selection':
                                if hasattr(v.selection, "__iter__"):
                                        properties['selection_keys'] = unicode(
                                                sorted([x[0] for x in v.selection]))
                                else:
                                        properties['selection_keys'] = 'function'
                        if v.required and k in model._defaults:
                                if isinstance(model._defaults[k], types.FunctionType):
                                        # todo: in OpenERP 5 (and in 6 as well),
                                        # literals are wrapped in a lambda function.
                                        properties['req_default'] = 'function'
                                else:
                                        properties['req_default'] = unicode(model._defaults[k])
                                        for key, value in properties.items():
                                                if value:
                                                        model_registry.setdefault(k, {})[key] = value

        def get_record_id(cr, module, model, field, mode):
            """
            OpenUpgrade: get or create the id from the record table matching
            the key parameter values
            """
            cr.execute(
                "SELECT id FROM openupgrade_record "
                "WHERE module = %s AND model = %s AND "
                "field = %s AND mode = %s AND type = %s",
                (module, model, field, mode, 'field')
                )
            record = cr.fetchone()
            if record:
                return record[0]
            cr.execute(
                "INSERT INTO openupgrade_record "
                "(module, model, field, mode, type) "
                "VALUES (%s, %s, %s, %s, %s)",
                (module, model, field, mode, 'field')
                )
            cr.execute(
                "SELECT id FROM openupgrade_record "
                "WHERE module = %s AND model = %s AND "
                "field = %s AND mode = %s AND type = %s",
                (module, model, field, mode, 'field')
                )
            return cr.fetchone()[0]

        def compare_registries(cr, module):
            """
            OpenUpgrade: Compare the local registry with the global registry,
            log any differences and merge the local registry with
            the global one.
            """
            if not table_exists(cr, 'openupgrade_record'):
                return
            for model, fields in local_registry.items():
                registry.setdefault(model, {})
                for field, attributes in fields.items():
                    old_field = registry[model].setdefault(field, {})
                    mode = old_field and 'modify' or 'create'
                    record_id = False
                    for key, value in attributes.items():
                        if key not in old_field or old_field[key] != value:
                            if not record_id:
                                record_id = get_record_id(
                                    cr, module, model, field, mode)
                            cr.execute(
                                "SELECT id FROM openupgrade_attribute "
                                "WHERE name = %s AND value = %s AND "
                                "record_id = %s",
                                (key, value, record_id)
                                )
                            if not cr.fetchone():
                                cr.execute(
                                    "INSERT INTO openupgrade_attribute "
                                    "(name, value, record_id) VALUES (%s, %s, %s)",
                                    (key, value, record_id)
                                    )
                                old_field[key] = value

	for package in graph:
		status['progress'] = (float(statusi)+0.1)/len(graph)
		m = package.name
		logger.notifyChannel('init', netsvc.LOG_INFO, 'addon:%s' % m)
		sys.stdout.flush()
		pool = pooler.get_pool(cr.dbname)
		modules = pool.instanciate(m)
		cr.execute('select state, demo from ir_module_module where name=%s', (m,))
		(package_state, package_demo) = (cr.rowcount and cr.fetchone()) or ('uninstalled', False)
		idref = {}
		status['progress'] = (float(statusi)+0.4)/len(graph)

                local_registry = {}
                for model in modules:
                        log_model(model)
                        compare_registries(cr, package.name)

		if hasattr(package, 'init') or hasattr(package, 'update') or package_state in ('to install', 'to upgrade'):
			init_module_objects(cr, m, modules)
			for kind in ('init', 'update'):
				for filename in package.datas.get('%s_xml' % kind, []):
					mode = 'update'
					if hasattr(package, 'init') or package_state=='to install':
						mode = 'init'
					logger.notifyChannel('init', netsvc.LOG_INFO, 'addon:%s:loading %s' % (m, filename))
					name, ext = os.path.splitext(filename)
					if ext == '.csv':
						tools.convert_csv_import(cr, m, os.path.basename(filename), tools.file_open(opj(m, filename)).read(), idref, mode=mode)
					elif ext == '.sql':
						queries = tools.file_open(opj(m, filename)).read().split(';')
						for query in queries:
							new_query = ' '.join(query.split())
							if new_query:
								cr.execute(new_query)
					else:
						tools.convert_xml_import(cr, m, tools.file_open(opj(m, filename)).read(), idref, mode=mode, **kwargs)
			if hasattr(package, 'demo') or (package_demo and package_state != 'installed'):
				status['progress'] = (float(statusi)+0.75)/len(graph)
				for xml in package.datas.get('demo_xml', []):
					name, ext = os.path.splitext(xml)
					logger.notifyChannel('init', netsvc.LOG_INFO, 'addon:%s:loading %s' % (m, xml))
					if ext == '.csv':
						tools.convert_csv_import(cr, m, os.path.basename(xml), tools.file_open(opj(m, xml)).read(), idref, noupdate=True)
					else:
						tools.convert_xml_import(cr, m, tools.file_open(opj(m, xml)).read(), idref, noupdate=True, **kwargs)
				cr.execute('update ir_module_module set demo=%s where name=%s', (True, package.name))
			package_todo.append(package.name)
			cr.execute("update ir_module_module set state='installed' where state in ('to upgrade', 'to install') and name=%s", (package.name,))
		cr.commit()
		statusi+=1

	pool = pooler.get_pool(cr.dbname)
	pool.get('ir.model.data')._process_end(cr, 1, package_todo)
	cr.commit()

def register_classes():
	module_list = os.listdir(ad)
	for package in create_graph(module_list):
		m = package.name
		logger.notifyChannel('init', netsvc.LOG_INFO, 'addon:%s:registering classes' % m)
		sys.stdout.flush()

		if not os.path.isfile(opj(ad, m+'.zip')):
			# XXX must restrict to only addons paths
			imp.load_module(m, *imp.find_module(m))
		else:
			import zipimport
			mod_path = opj(ad, m+'.zip')
			try:
				zimp = zipimport.zipimporter(mod_path)
				zimp.load_module(m)
			except zipimport.ZipImportError:
				logger.notifyChannel('init', netsvc.LOG_ERROR, 'Couldn\'t find module %s' % m)

def load_modules(db, force_demo=False, status=None, update_module=False):
	if not status:
		status={}
	cr = db.cursor()
	force = []
	if force_demo:
		force.append('demo')
	if update_module:
		cr.execute("select name from ir_module_module where state in ('installed', 'to install', 'to upgrade','to remove')")
	else:
		cr.execute("select name from ir_module_module where state in ('installed', 'to upgrade', 'to remove')")
	module_list = [name for (name,) in cr.fetchall()]
	graph = create_graph(module_list, force)
	report = tools.assertion_report()
        registry = {}
        try:
                load_module_graph(cr, graph, status, registry=registry, report=report)
        except Exception, e:
                print e
                raise
	if report.get_report():
		logger.notifyChannel('init', netsvc.LOG_INFO, 'assert:%s' % report)

	for kind in ('init', 'demo', 'update'):
		tools.config[kind]={}

	cr.commit()
	if update_module:
		cr.execute("select id,name from ir_module_module where state in ('to remove')")
		for mod_id, mod_name in cr.fetchall():
			pool = pooler.get_pool(cr.dbname)
			cr.execute('select model,res_id from ir_model_data where not noupdate and module=%s order by id desc', (mod_name,))
			for rmod,rid in cr.fetchall():
				#
				# TO BE Improved:
				#   I can not use the class_pool has _table could be defined in __init__
				#   and I can not use the pool has the module could not be loaded in the pool
				#
				uid = 1
				pool.get(rmod).unlink(cr, uid, [rid])
			cr.commit()
		#
		# TODO: remove menu without actions of childs
		#
		cr.execute('''delete from
				ir_ui_menu
			where
				(id not in (select parent_id from ir_ui_menu where parent_id is not null))
			and
				(id not in (select res_id from ir_values where model='ir.ui.menu'))
			and
				(id not in (select res_id from ir_model_data where model='ir.ui.menu'))''')

		cr.execute("update ir_module_module set state=%s where state in ('to remove')", ('uninstalled', ))
		cr.commit()
		pooler.restart_pool(cr.dbname)
	cr.close()

