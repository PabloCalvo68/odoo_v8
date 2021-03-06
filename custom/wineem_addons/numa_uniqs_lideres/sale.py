# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2012 NUMA Extreme Systems (<http:www.numaes.com>).
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

from openerp.osv import fields, osv
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import netsvc

class campaign(osv.osv):
    _name = "sale.campaign"
    
    _columns = {
        'name': fields.char ('Name', size=32),
    }

campaign()

class sale_order (osv.osv):

    _inherit = "sale.order"
    
    _columns = {
        'campaign': fields.many2one('sale.campaign', 'Campaign', required=True),
        'leader_id': fields.related('partner_id','leader_id', string="Leader", type="many2one", relation="res.partner", readonly=True),
        'state': fields.selection([
            ('draft', 'Quotation'),
            ('waiting_date', 'Waiting Schedule'),
            ('manual', 'Manual In Progress'),
            ('progress', 'In Progress'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
            ('prepared', 'Prepared'),
            ], 'Order State', readonly=True, help="Gives the state of the quotation or sales order. \nThe exception state is automatically set when a cancel operation occurs in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception). \nThe 'Waiting Schedule' state is set when the invoice is confirmed but waiting for the scheduler to run on the date 'Ordered Date'.", select=True),
    }
    
    def action_back_to_draft(self, cr, uid, ids, context=None):
        for so in self.browse(cr, uid, ids, context=context):
            if so.state == "prepared":
                so.write({'state': 'draft'})
        return True

    def action_recalculate_order(self, cr, uid, ids, context=None):
        for so in self.browse(cr, uid, ids, context=context):
            if so.state == "prepared":
                so.write({'pricelist_id': so.partner_id.property_product_pricelist.id})
                so.action_recompute_pricelist()
        return True

    def create(self, cr, uid, vals, context=None):
        vals_copy = vals.copy()
        vals_copy['state'] = 'prepared'
        vals_copy['warehouse_id'] = 1
        return super(sale_order, self).create(cr, uid, vals_copy, context=context)

    def action_ship_create(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        picking_id = False
        move_obj = self.pool.get('stock.move')
        proc_obj = self.pool.get('procurement.order')
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        for order in self.browse(cr, uid, ids, context={}):
            proc_ids = []
            #output_id = order.shop_id.warehouse_id.lot_output_id.id
            output_id = order.warehouse_id.wh_output_stock_loc_id.id
            picking_id = False
            for line in order.order_line:
                proc_id = False
                date_planned = datetime.now() + relativedelta(days=line.delay or 0.0)
                date_planned = (date_planned - timedelta(days=company.security_lead)).strftime('%Y-%m-%d %H:%M:%S')

                if line.state == 'done':
                    continue
                move_id = False
                if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    #location_id = order.shop_id.warehouse_id.lot_stock_id.id
                    location_id = order.warehouse_id.lot_stock_id.id
                    if not picking_id:
                        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
                        picking_id = self.pool.get('stock.picking').create(cr, uid, {
                            'name': pick_name,
                            'origin': order.name,
                            'type': 'out',
                            'state': 'draft',
                            'move_type': order.picking_policy,
                            'sale_id': order.id,
                            'address_id': order.partner_shipping_id.id,
                            'note': order.note,
                            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
                            'company_id': order.company_id.id,
                            'campaign': order.campaign and order.campaign.id or False,
                            'picking_type_id': 2 #Venta (outgoing)
                        })
                    move_id = self.pool.get('stock.move').create(cr, uid, {
                        'name': line.name[:64],
                        'picking_id': picking_id,
                        'product_id': line.product_id.id,
                        'date': date_planned,
                        'date_expected': date_planned,
                        #'product_qty': line.product_uom_qty,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_uos_qty,
                        'product_uos': (line.product_uos and line.product_uos.id)\
                                or line.product_uom.id,
                        'product_packaging': line.product_packaging.id,
                        'address_id': line.address_allotment_id.id or order.partner_shipping_id.id,
                        'location_id': location_id,
                        'location_dest_id': output_id,
                        'sale_line_id': line.id,
                        'tracking_id': False,
                        'state': 'draft',
                        #'state': 'waiting',
                        #'note': line.notes,
                        'company_id': order.company_id.id,
                    })

                if line.product_id:
                    proc_id = self.pool.get('procurement.order').create(cr, uid, {
                        'name': line.name,
                        'origin': order.name,
                        'date_planned': date_planned,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': (line.product_uos and line.product_uos_qty)\
                                or line.product_uom_qty,
                        'product_uos': (line.product_uos and line.product_uos.id)\
                                or line.product_uom.id,
                        #'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
                        'location_id': order.warehouse_id.lot_stock_id.id,
                        #'procure_method': line.type,
                        'move_id': move_id,
                        #'property_ids': [(6, 0, [x.id for x in line.property_ids])],
                        'company_id': order.company_id.id,
                    })
                    proc_ids.append(proc_id)
                    self.pool.get('sale.order.line').write(cr, uid, [line.id], {'procurement_id': proc_id})
                    if order.state == 'shipping_except':
                        for pick in order.picking_ids:
                            for move in pick.move_lines:
                                if move.state == 'cancel':
                                    mov_ids = move_obj.search(cr, uid, [('state', '=', 'cancel'),('sale_line_id', '=', line.id),('picking_id', '=', pick.id)])
                                    if mov_ids:
                                        for mov in move_obj.browse(cr, uid, mov_ids):
                                            move_obj.write(cr, uid, [move_id], {'product_qty': mov.product_uom_qty, 'product_uos_qty': mov.product_uos_qty})
                                            proc_obj.write(cr, uid, [proc_id], {'product_qty': mov.product_uom_qty, 'product_uos_qty': mov.product_uos_qty})

            val = {}

            if picking_id:
                wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)

            for proc_id in proc_ids:
                wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

            if order.state == 'shipping_except':
                val['state'] = 'progress'
                val['shipped'] = False

                if (order.order_policy == 'manual'):
                    for line in order.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            val['state'] = 'manual'
                            break
            self.write(cr, uid, [order.id], val)
        return True
        
sale_order()

class sale_order_massive_change(osv.osv_memory):
    _name = "sale.so_massive_state_change"

    _columns = {
        'campaign': fields.many2one('sale.campaign', 'Campaign', required=True),
    }    
    
    def action_change_to_draft(self, cr, uid, ids, context=None):
        so_obj = self.pool.get('sale.order')
        so_ids = context.get('active_ids', [context.get('active_id')])
        
        assert ids and len(ids)==1        
        msc = self.browse(cr, uid, ids[0], context=context)
        
        if so_ids:
            so_obj.write(cr, uid, so_ids, {'campaign': msc.campaign.id}, context=context)
            so_obj.action_back_to_draft(cr, uid, so_ids, context=context)

        return {'type': 'ir.actions.act_window_close'}

sale_order_massive_change()
