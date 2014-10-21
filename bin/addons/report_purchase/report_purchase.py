##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: purchase.py 1005 2005-07-25 08:41:42Z nicoe $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
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

#
# Please note that these reports are not multi-currency !!!
#

from osv import fields,osv

class report_purchase_order_product(osv.osv):
	_name = "report.purchase.order.product"
	_description = "Purchases Orders by Products"
	_auto = False
	_columns = {
		'name': fields.date('Month', readonly=True),
		'state': fields.selection([
			('draft','Quotation'),
			('waiting_date','Waiting Schedule'),
			('manual','Manual in progress'),
			('progress','In progress'),
			('shipping_except','Shipping Exception'),
			('invoice_except','Invoice Exception'),
			('done','Done'),
			('cancel','Cancel')
		], 'Order State', readonly=True),
		'product_id':fields.many2one('product.product', 'Product', readonly=True),
		'quantity': fields.float('# of Products', readonly=True),
		'price_total': fields.float('Total Price', readonly=True),
		'price_average': fields.float('Average Price', readonly=True),
		'count': fields.integer('# of Lines', readonly=True),
	}
	_order = 'name desc,price_total desc'
	def init(self, cr):
		cr.execute("""
			create or replace view report_purchase_order_product as (
				select
					min(l.id) as id,
					to_char(s.date_order, 'YYYY-MM')||'-'||'01' as name,
					s.state,
					l.product_id,
					sum(l.product_qty*u.factor) as quantity,
					count(*),
					sum(l.product_qty*l.price_unit) as price_total,
					(sum(l.product_qty*l.price_unit)/sum(l.product_qty*u.factor))::decimal(16,2) as price_average
				from purchase_order s
					left join purchase_order_line l on (s.id=l.order_id)
					left join product_uom u on (u.id=l.product_uom)
				group by l.product_id, to_char(s.date_order, 'YYYY-MM'),s.state
			)
		""")
report_purchase_order_product()

class report_purchase_order_category(osv.osv):
	_name = "report.purchase.order.category"
	_description = "Purchases Orders by Categories"
	_auto = False
	_columns = {
		'name': fields.date('Month', readonly=True),
		'state': fields.selection([
			('draft','Quotation'),
			('waiting_date','Waiting Schedule'),
			('manual','Manual in progress'),
			('progress','In progress'),
			('shipping_except','Shipping Exception'),
			('invoice_except','Invoice Exception'),
			('done','Done'),
			('cancel','Cancel')
		], 'Order State', readonly=True),
		'category_id': fields.many2one('product.category', 'Categories', readonly=True),
		'quantity': fields.float('# of Products', readonly=True),
		'price_total': fields.float('Total Price', readonly=True),
		'price_average': fields.float('Average Price', readonly=True),
		'count': fields.integer('# of Lines', readonly=True),
	}
	_order = 'name desc,price_total desc'
	def init(self, cr):
		cr.execute("""
			create or replace view report_purchase_order_category as (
				select
					min(l.id) as id,
					to_char(s.date_order, 'YYYY-MM')||'-'||'01' as name,
					s.state,
					t.categ_id as category_id,
					sum(l.product_qty*u.factor) as quantity,
					count(*),
					sum(l.product_qty*l.price_unit) as price_total,
					(sum(l.product_qty*l.price_unit)/sum(l.product_qty*u.factor))::decimal(16,2) as price_average
				from purchase_order s
					left join purchase_order_line l on (s.id=l.order_id)
					left join product_product p on (p.id=l.product_id)
					left join product_template t on (t.id=p.product_tmpl_id)
					left join product_uom u on (u.id=l.product_uom)
				group by t.categ_id, to_char(s.date_order, 'YYYY-MM'),s.state
			 )
		""")
report_purchase_order_category()
