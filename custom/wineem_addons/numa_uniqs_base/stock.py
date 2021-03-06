# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2011 NUMA Extreme Systems (<http:www.numaes.com>).
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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp import netsvc

import pdb

class stock_location(osv.osv):
    _inherit = "stock.location"

    _columns = {
        'afip_store_point_id': fields.many2one ('numa_ar_base.afip_store_point', 'AFIP Store point', help='AFIP Store point used to get official sequences'),
    }

stock_location()

class stock_picking(osv.osv):
    _inherit = "stock.picking"


    def _invoice_hook(self, cr, uid, picking, invoice_id):
        '''Call after the creation of the invoice'''
        super(stock_picking, self)._invoice_hook (cr, uid, picking, invoice_id)

        if picking.sale_id:
            picking.sale_id.write({'invoice_ids': [(4, invoice_id)]})
            
        # todo liricus elf.pool.get('account.invoice').write (cr, uid, [invoice_id], {'shop_id': picking.shop_id.id})
        self.pool.get('account.invoice').write(cr, uid, [invoice_id])

        return

    def _invoice_line_hook(self, cr, uid, move_line, invoice_line_id):
        if move_line.sale_line_id:
            move_line.sale_line_id.write({
                'invoice_lines': [(4, invoice_line_id)],
                'price_unit': move_line.sale_line_id.price_unit,
                'discount': move_line.sale_line_id.discount,
            })

    _columns = {
        #'shop_id': fields.many2one ('sale.shop', 'Shop', help='Issuing shop', readonly=True, states={'draft':[('readonly',False)]}),
        'afip_id': fields.float ('AFIP store point', digits=(4,0), readonly=True, states={'draft':[('readonly',False)]}),
        'afip_number': fields.float ('AFIP number', digits=(8,0), readonly=True, states={'draft':[('readonly',False)]}),
    }

    def action_done(self, cr, uid, ids, context=None):
        for sp in self.browse (cr, uid, ids, context=context):
            if sp.picking_type_id.code == 'outgoing':

                to_location = None
                from_location = None
                for ml in sp.move_lines:
                    if ml.location_dest_id:
                        to_location = ml.location_dest_id
                        from_location = ml.location_id
                        break

                if to_location and to_location.usage == "customer" and from_location.afip_store_point_id:
                    store_point = from_location.afip_store_point_id

                    new_name = "OUT/RE %04d-%08d" % (store_point.afip_id, store_point.r_next_number)
                    self.write (cr, uid, [sp.id], {'afip_id': store_point.afip_id, 'afip_number': store_point.r_next_number}, context=context)

                    afip_store_obj = self.pool.get('numa_ar_base.afip_store_point')
                    afip_store_obj.write (cr, uid, [store_point.id], {'r_next_number': store_point.r_next_number+1})

                    self.write (cr, uid, [sp.id], {'name': new_name, 'company_id': store_point.company_id.id}, context=context)
              
        return super (stock_picking, self).action_done(cr, uid, ids, context=context)

    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):

        invoice_obj = self.pool.get('account.invoice')
        res = super(stock_picking, self).action_invoice_create(cr, uid, ids, journal_id, group, type, context)
        #Set the generating out picking
        i = 0
        for invoice_id in res:
            picking_id = ids[i]
            invoice_obj.write(cr, uid, [invoice_id], {'out_picking': picking_id})
            i += 1
        return res

    def create(self, cr, user, vals, context=None):
        if 'sale_id' in vals:
            sale_obj = self.pool.get('sale.order')
            sale = sale_obj.browse(cr, 1, vals['sale_id'], context=context)
            vals['partner_id'] = sale.partner_id.id
        return super(stock_picking, self).create(cr, user, vals, context)

stock_picking()


class stock_invoice_onshipping(osv.osv_memory):
    _inherit = "stock.invoice.onshipping"

    def _get_journal_id(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users')
        
        if context is None:
            context = {}

        model = context.get('active_model')
        if not model or model != 'stock.picking':
            return []

        model_pool = self.pool.get(model)
        journal_obj = self.pool.get('account.journal')
        res_ids = context and context.get('active_ids', [])
        vals = []
        browse_picking = model_pool.browse(cr, uid, res_ids, context=context)
        user = user_obj.browse(cr, 1, uid, context=context)
        
        for pick in browse_picking:
            
            company_id = pick.company_id.id
            src_usage = pick.move_lines[0].location_id and pick.move_lines[0].location_id.usage or ''
            dest_usage = pick.move_lines[0].location_dest_id and pick.move_lines[0].location_dest_id.usage or ''
            # ver en odoo si pick.type es algo de esto..
            # pick.picking_type_code
            # pick.move_type
            #todo liricus se cambio pick.type por pick.picking_type_code
            # type = pick.type
            type = pick.picking_type_code
            if type == "outgoing":
                type = "out"
            if type == "incoming":
                type = "in"
            if type == 'out' and dest_usage == 'supplier':
                journal_type = 'purchase_refund'
            elif type == 'out' and dest_usage == 'customer':
                journal_type = 'sale'
            elif type == 'in' and src_usage == 'supplier':
                journal_type = 'purchase'
            elif type == 'in' and src_usage == 'customer':
                journal_type = 'sale_refund'
            else:
                journal_type = 'sale'

            #value = journal_obj.search(cr, uid, [('type', '=',journal_type ), ('company_id', '=', company_id)])
            journal_ids = journal_obj.search(cr, uid, [('type', '=',journal_type )])

            for journal in journal_obj.browse(cr, uid, journal_ids, context=context):
                if pick:
                    t1 = (journal.id, "%s [%s]" % (journal.name, journal.company_id.name))
                else:
                    t1 = (journal.id, "%s [%s]" % (journal.name, journal.company_id.name))

                if t1 not in vals:
                    vals.append(t1)
        return vals
        
    def _get_default_journal_id(self, cr, uid, context=None):
        selection = self._get_journal_id(cr, uid, context=context)
        if selection:
            return selection[0][0]
        else:
            return False,

    _columns = {
        'journal_id': fields.selection(_get_journal_id, 'Destination Journal',required=True),
        'company_id': fields.many2one('res.company', "Company", readonly=True),
        #'shop_id': fields.many2one('sale.shop', 'Shop', help="Shop to use for invoicing"),
    }

    _defaults = {
        'journal_id': lambda s, c, u, ctx: s._get_default_journal_id( c, u, context=ctx),     
    }

    def onchange_journal_id(self, cr, uid, ids, journal_id, context=None):
        res = {}
        if journal_id:
            journal_obj = self.pool.get('account.journal')
            # shop_obj = self.pool.get('sale.shop')

            journal = journal_obj.browse(cr, 1, journal_id, context=context)
            # shop_ids = shop_obj.search(cr, 1, [('company_id','=', journal.company_id and journal.company_id.id or False)], context=context)

            # if shop_ids:
            #     res['shop_id'] = shop_ids[0]
            res['company_id'] = journal.company_id and journal.company_id.id or False
        else:
            res['company_id'] = False
            
        return {'value': res}

    def fix_account(self, cr, uid, account_id, company_id):
        account_obj = self.pool.get('account.account')
        account = account_obj.browse(cr, uid, account_id)
        new_id = account.id
        changed = False
        if account.company_id.id != company_id:
            new_id = account_obj.search(cr, uid, [('name','=',account.name),('company_id','=',company_id)])[0]
            changed = True
        return new_id, changed

    def create_invoice(self, cr, uid, ids, context=None):

        property_obj = self.pool.get('ir.property')
        journal_mapping_type_inv = {
            'sale': 'out_invoice',
            'purchase': 'in_invoice',
            'sale_refund': 'out_refund',
            'purchase_refund': 'in_refund',
        }
        if context is None:
            context = {}
        picking_pool = self.pool.get('stock.picking')
        onshipdata_obj = self.read(cr, uid, ids, ['journal_id', 'company_id', 'group', 'invoice_date'])

        journal_pool = self.pool.get('account.journal')
        if context.get('new_picking', False):
            onshipdata_obj['id'] = onshipdata_obj.new_picking
            onshipdata_obj[ids] = onshipdata_obj.new_picking
        context['date_inv'] = onshipdata_obj[0]['invoice_date']
        active_ids = context.get('active_ids', [])

        journal_type = journal_pool.browse(cr, uid, int(onshipdata_obj[0]['journal_id'])).type
        company = journal_pool.browse(cr, uid, int(onshipdata_obj[0]['journal_id'])).company_id
        # todo liricus
        # shop_id = onshipdata_obj[0]['shop_id']
        inv_type = journal_mapping_type_inv[journal_type]
        context['inv_type'] = inv_type
        journal = journal_pool.browse(cr, uid, int(onshipdata_obj[0]['journal_id']))
        errores = False
        partners = []
        if journal.point_of_sale_id.type == "electronic":
            for picking in picking_pool.browse(cr, uid, active_ids, context=context):
                if not (picking.partner_id.document_number and picking.partner_id.responsability_id and \
                        picking.partner_id.document_type_id and picking.partner_id.vat_condition):
                    partners.append(picking.partner_id.name)
                    errores = True
        if errores:
            raise osv.except_osv(_('Error !'),
                                 _(u'Hay personas que requieren datos a configurar dni y condicion de iva: {}'.format(partners)))

        errores = False
        partners = []
        for picking in picking_pool.browse(cr, uid, active_ids, context=context):
            if not picking.partner_id.property_account_payable or not picking.partner_id.property_account_receivable:
                partners.append(picking.partner_id.name)
                errores = True
        if errores:
            raise osv.except_osv(_('Error !'),
                                 _(u'Hay personas que requieren configurar cuenta contable: {}'.format(partners)))

        res = picking_pool.action_invoice_create(cr, uid, active_ids,
              journal_id = int(onshipdata_obj[0]['journal_id']),
              group = onshipdata_obj[0]['group'],
              type = inv_type,
              context=context)

        #Fix invoice with selected shop_id and company_id(by default it will be created on picking.company_id)
        invoice_obj = self.pool.get('account.invoice')
        pick_obj = self.pool.get('stock.picking')
        sale_obj = self.pool.get('sale.order')
        for invoice_id in res:
            invoice_vat_amount = 0
            invoice_vat_base_amount = 0
            invoice = invoice_obj.browse(cr, uid, invoice_id, context=context)
            r = invoice.onchange_company_id(company.id, invoice.partner_id.id, invoice.type, [], invoice.currency_id.id)
            if r:
                invoice.write(r['value'])
            # invoice.write({'shop_id': shop_id, 'company_id': company.id})
            invoice.write({'company_id': company.id})
            invoice = invoice_obj.browse(cr, uid, invoice.id, context=context)
            # todo Liricus: comento en address_invoice_id luego verlo bien pero viene por invoice.partner_id
            for line in invoice.invoice_line:

                pick_id = pick_obj.search(cr, uid, [('name', '=', line.origin)], context=context)
                pick = pick_obj.browse(cr, uid, pick_id, context=context)
                sale_id = sale_obj.search(cr, uid, [('name', '=', pick.origin)], context=context)
                sale = sale_obj.browse(cr, uid, sale_id, context=context)
                order_line = sale.order_line.filtered(lambda r: r.product_id.id == line.product_id.id)

                price_unit = order_line.price_unit
                discount = order_line.discount
                price_subtotal = order_line.price_subtotal
                vat_amount = order_line.vat_amount
                # invoice_vat_amount += order_line.vat_amount
                # invoice_vat_base_amount += order_line.price_subtotal
                r = line.product_id_change(line.product_id.id,
                                           line.uos_id and line.uos_id.id or False,
                                           qty=line.quantity,
                                           name=line.name,
                                           type=invoice.type,
                                           partner_id=1,
                                           fposition_id=invoice.fiscal_position and invoice.fiscal_position.id or False,
                                           price_unit=price_unit,
                                           # discount=discount,
                                           # vat_amount=vat_amount,
                                           # address_invoice_id = invoice.address_invoice_id and invoice.address_invoice_id.id or False,
                                           currency_id = invoice.currency_id and invoice.currency_id.id or False
                                           # context=context
                     )
                if r:
                    # if 'price_unit' in r['value']:
                    #     del r['value']['price_unit']
                    # if 'discount' in r['value']:
                    #     del r['value']['discount']
                    # if 'invoice_line_tax_id' in r['value']:
                    #     # Adapt from UI format to server format for write
                    #     r['value']['invoice_line_tax_id'] = [(4, x) for x in r['value']['invoice_line_tax_id']]

                    r['value']['price_unit'] = price_unit
                    r['value']['discount'] = discount
                    r['value']['price_subtotal'] = price_subtotal
                    r['value']['vat_amount'] = vat_amount
                    line.write(r['value'])
            invoice.button_reset_taxes()
        return res

stock_invoice_onshipping()

class stock_move (osv.osv):
    _inherit = "stock.move"

    def _create_chained_picking(self, cr, uid, pick_name, picking, ptype, move, context=None):
        res = super(stock_move, self)._create_chained_picking(cr, uid, pick_name, picking, ptype, move, context=context)
        if res:
            self.pool.get('stock.picking').write(cr, uid, [res], {'invoice_state': picking.invoice_state})
        return res

stock_move()
