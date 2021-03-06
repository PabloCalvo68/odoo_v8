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

from openerp.osv import osv, fields
from openerp.tools.translate import _

SUPERUSER = 1
PARCHE_INICIAL = True


class res_partner(osv.osv):

    _inherit = "res.partner"

    _columns = {
        'fechadenacimiento': fields.char('Fecha de nacimiento', size=128),
        'localidad': fields.char(u'Localidad', size=128),
        'provincia': fields.char(u'Provincia', size=128),
        'direccioncliente': fields.char(u'Dirección cliente', size=128),
        'cierre': fields.char(u'Cierre', size=128),
    }

    def create (self, cr, uid, vals, context=None):
        field_obj = self.pool.get('ir.model.fields')
        property_obj = self.pool.get('ir.property')
        account_obj = self.pool.get('account.account')
        account_type_obj = self.pool.get('account.account.type')
        partner_obj = self.pool.get('res.partner')
        closing_obj = self.pool.get('res.partner.closing')
        sale_commission_obj = self.pool.get('sale.commission')
        safe_vals = None
        new_partner_id = None

        #todo creo que aca por el else deberia poner un pass para que no cree un cliente tipo factura
        if vals.get('category_id') and vals.get('category_id')[0][1] > 0:
            vals["group_id"] = vals.get('category_id')[0][1]

        if vals.get('cierre'):
            cierre = vals.get('cierre')
            parfield_ids = closing_obj.search(cr, uid, [('id_magento', '=', cierre)])
            parfield = closing_obj.browse(cr, uid, parfield_ids[0], context=context)
            vals['cierre'] = parfield.name
            vals['commercial_closing'] = parfield.id

        safe_vals = vals.copy()
        # print "create %s" % safe_vals
        # print "create new_partner_id  %s" % new_partner_id

        #todo liricus:  esto lo voy a poner para importar solo los representantes... luego lo comento
        # if PARCHE_INICIAL:
        #     if vals.get('group_id', None) and not vals.get('parent_id', None):
        #         cat_obj = self.pool.get('res.partner.category')
        #         category = cat_obj.browse(cr, uid, vals['group_id'], context=context)
        #         if category.name != 'RESPONSABLES':
        #             return 0

        new_partner_id = super(res_partner, self).create(cr, uid, safe_vals, context=context)
        if vals.get('group_id', None) and not vals.get('parent_id', None):
            #Update property_account_receivable according to magento group

            parfield_ids = field_obj.search(cr, uid, [('name','=','property_account_receivable'),('model','=','res.partner')])
            parfield = field_obj.browse(cr, uid, parfield_ids[0], context=context)

            parfield_ids = field_obj.search(cr, uid, [('name','=','property_product_pricelist'),('model','=','res.partner')])
            parfield_pricelist = field_obj.browse(cr, uid, parfield_ids[0], context=context)

            account_obj = self.pool.get ('account.account')
            cat_obj = self.pool.get ('res.partner.category')
            category = cat_obj.browse (cr, uid, vals['group_id'], context=context)
            if category.name != 'RESPONSABLES':
                parent_ids = self.search(cr, SUPERUSER, [('name','=',category.name.replace('_',' ')),('group_id.name','=','RESPONSABLES')], context=context)
                if parent_ids:
                    self.write(cr, SUPERUSER, [new_partner_id], {'parent_id': parent_ids[0]}, context=context)
                new_partner = self.browse(cr, SUPERUSER, new_partner_id, context=context)
                if new_partner.parent_id and not vals.get('property_product_pricelist', None):
                    parent_ids = property_obj.search(cr, SUPERUSER, [('name','=','property_product_pricelist'),('res_id','=','res.partner,%d' % new_partner.parent_id.id)])
                    props = [(p.company_id.id, p.value_reference.id) for p in property_obj.browse(cr, SUPERUSER, parent_ids, context=context)]

                    current_ids = property_obj.search(cr, SUPERUSER, [('name','=','property_product_pricelist'),('res_id','=','res.partner,%d' % new_partner.id)])
                    if current_ids:
                        property_obj.unlink(cr, SUPERUSER, current_ids)

                    for company_id, value_id in props:
                        property_obj.create(cr, SUPERUSER, {
                            'name': 'property_product_pricelist',
                            'company_id': company_id,
                            'fields_id': parfield_pricelist.id,
                            'res_id': 'res.partner,%d' % new_partner_id,
                            'type': 'many2one',
                            'value': value_id,
                        })
                accounts_ids = account_obj.search (cr, SUPERUSER, [('code','=','receivable'),('name','=',category.name.replace('_',' '))], context=context)
            else:
                # It is a new REPRESENTANTE: Create accounts if needed
                receivable_ids = account_type_obj.search(cr, SUPERUSER, [('code','=','receivable')], context=context)
                if not receivable_ids:
                    raise osv.except_osv(_('Error !'), _("No account user type 'Receivable' found! Please check it"))
                receivable_id = receivable_ids[0]
                root_account_ids = account_obj.search (cr, SUPERUSER, [('code','=','110201')], context=context)
                accounts_ids = []
                for root_account in account_obj.browse(cr, SUPERUSER, root_account_ids, context=context):
                    children_ids = account_obj.search(cr, SUPERUSER, [('parent_id','=',root_account.id)], order="code desc", limit=1, context=context)
                    if children_ids:
                        last_child = account_obj.browse(cr, SUPERUSER, children_ids[0], context=context)
                        next_code = str(int(last_child.code)+1)
                    else:
                        next_code = root_account.code[0:-1] + '00001'
                    accounts_ids.append(
                        account_obj.create (cr, SUPERUSER, {
                            'code': next_code,
                            'name': vals.get('name','').upper(),
                            'type': 'receivable',
                            'user_type': receivable_id,
                            'parent_id': root_account.id,
                            'company_id': root_account.company_id.id,
                            'reconcile': True
                        }, context=context)
                    )

                new_partner = self.browse(cr, SUPERUSER, new_partner_id, context=context)
                vals = {'name': new_partner.name.upper(), "agent": True}
                # Esto va en duro.. traigo la commision con id 1
                sale_com = sale_commission_obj.browse(cr, SUPERUSER, [1], context=context)
                if sale_com and not new_partner.commission:
                    vals['commission'] = sale_com.id
                new_partner.write(vals, context=context)

                # parent_ids = property_obj.search(cr, SUPERUSER, [('name', '=', 'property_product_pricelist'), (
                # 'res_id', '=', 'res.partner,%d' % new_partner_id)])
                # props = [(p.company_id.id, p.value_reference.id) for p in
                #          property_obj.browse(cr, SUPERUSER, parent_ids, context=context)]
                #
                # current_ids = property_obj.search(cr, SUPERUSER, [('name','=','property_product_pricelist'),('res_id','=','res.partner,%d' % new_partner.id)])
                # if current_ids:
                #     property_obj.unlink(cr, SUPERUSER, current_ids)
                #
                # for company_id, value_id in props:
                #     property_obj.create(cr, SUPERUSER, {
                #         'name': 'property_product_pricelist',
                #         'company_id': company_id,
                #         'fields_id': parfield_pricelist.id,
                #         'res_id': 'res.partner,%d' % new_partner_id,
                #         'type': 'many2one',
                #         'value': value_id,
                #     })

            if accounts_ids:
                for account in account_obj.browse(cr, SUPERUSER, accounts_ids, context=context):
                    current_ids = property_obj.search(cr, SUPERUSER, [('name','=','property_account_receivable'),('company_id','=', account.company_id.id),('res_id','=','res.partner,%d' % new_partner_id)])
                    if current_ids:
                        property_obj.unlink(cr, SUPERUSER, current_ids)

                    property_obj.create(cr, SUPERUSER, {
                        'name': 'property_account_receivable',
                        'company_id': account.company_id.id,
                        'fields_id': parfield.id,
                        'res_id': 'res.partner,%d' % new_partner_id,
                        'type': 'many2one',
                        'value': account.id
                    })
        return new_partner_id

    def write(self, cr, uid, ids, vals, context=None):

        field_obj = self.pool.get('ir.model.fields')
        property_obj = self.pool.get('ir.property')
        account_obj = self.pool.get('account.account')
        cat_obj = self.pool.get ('res.partner.category')
        partner_obj = self.pool.get ('res.partner')
        account_type_obj = self.pool.get('account.account.type')
        closing_obj = self.pool.get('res.partner.closing')

        if vals.get('cierre'):
            cierre = vals.get('cierre')
            parfield_ids = closing_obj.search(cr, uid, [('id_magento', '=', cierre)])
            parfield = closing_obj.browse(cr, uid, parfield_ids[0], context=context)
            vals['cierre'] = parfield.name
            vals['commercial_closing'] = parfield.id

        safe_vals = vals.copy()
        # print "save %s" % safe_vals
        if isinstance(ids, (int, long)):
            ids = [ids]
        # print "save id %s" % ids
        partner = partner_obj.browse(cr, uid, ids, context=context)
        # esto es para que no se pise el nombre cdo viene desde company
        if partner:
            name = vals.get('name', None)
            company = vals.get('company', None)
            if name and company and name == company:
                # print "Esto es para que no se pise el nombre %s" % safe_vals
                saco_nombre = safe_vals.pop('name', None)
            else:
                zip = vals.get('zip', None)
                if zip:
                    saco_nombre = safe_vals.pop('name', None)
        # print "save name %s" % safe_vals

        #todo liricus esto lo voy a poner para importar solo los representantes... luego lo comento
        # if PARCHE_INICIAL:
        #     if vals.get('group_id', None):
        #         cat_obj = self.pool.get('res.partner.category')
        #         category = cat_obj.browse(cr, uid, vals['group_id'], context=context)
        #         if category.name != 'RESPONSABLES':
        #             return 0

        res = super(res_partner, self).write(cr, uid, ids, safe_vals, context=context)
        parfield_ids = field_obj.search(cr, uid, [('name','=','property_account_receivable'),('model','=','res.partner')])
        parfield = field_obj.browse(cr, uid, parfield_ids[0], context=context)

        if vals.get('group_id', None):
            category = cat_obj.browse(cr, uid, vals['group_id'], context=context)
            if category.name != 'RESPONSABLES':
                parent_ids = self.search(cr, uid, [('name','=',category.name.replace('_',' ')),('group_id.name','=','RESPONSABLES')], context=context)
                if parent_ids:
                    self.write(cr, uid, ids, {'parent_id': parent_ids[0]}, context=context)
                    accounts_ids = account_obj.search (cr, SUPERUSER, [('code','=','receivable'),('name','=',category.name.replace('_',' '))], context=context)
                    for partner in self.browse(cr, SUPERUSER, ids, context=context):
                        if partner.parent_id and not vals.get('property_product_pricelist', None):
                            partner.write({'property_product_pricelist': partner.parent_id.property_product_pricelist and partner.parent_id.property_product_pricelist.id or None})
                        for account in account_obj.browse(cr, SUPERUSER, accounts_ids, context=context):
                            current_ids = property_obj.search(cr, SUPERUSER, [('name','=','property_account_receivable'),('company_id','=', account.company_id.id),('res_id','=','res.partner,%d' % partner.id)])
                            if current_ids:
                                property_obj.unlink(cr, SUPERUSER, current_ids)

                            property_obj.create(cr, SUPERUSER, {
                                'name': 'property_account_receivable',
                                'company_id': account.company_id.id,
                                'fields_id': parfield.id,
                                'res_id': 'res.partner,%d' % partner.id,
                                'type': 'many2one',
                                'value': account.id
                            })
                else:
                    self.write(cr, uid, ids, {'parent_id': None}, context=context)
            else:
                # It is a rep
                receivable_ids = account_type_obj.search(cr, SUPERUSER, [('code','=','receivable')], context=context)
                if not receivable_ids:
                    raise osv.except_osv(_('Error !'), _("No account user type 'Receivable' found! Please check it"))
                receivable_id = receivable_ids[0]
                root_account_ids = account_obj.search (cr, SUPERUSER, [('code','=','110201')], context=context)
                accounts_ids = []
                for root_account in account_obj.browse(cr, SUPERUSER, root_account_ids, context=context):
                    for partner in self.browse(cr, SUPERUSER, ids, context=context):
                        id_account_ids = account_obj.search(cr, SUPERUSER, [('parent_id','=',root_account.id),('name','=',partner.name.upper())], context=context)
                        if not id_account_ids:
                            children_ids = account_obj.search(cr, SUPERUSER, [('parent_id','=',root_account.id)], order="code desc", limit=1, context=context)
                            if children_ids:
                                last_child = account_obj.browse(cr, SUPERUSER, children_ids[0], context=context)
                                next_code = str(int(last_child.code)+1)
                            else:
                                next_code = root_account.code[0:-1] + '00001'

                            account_id = 0
                            account_id = account_obj.create (cr, SUPERUSER, {
                                            'code': next_code,
                                            'name': vals.get('name', partner.name.upper()),
                                            'type': 'receivable',
                                            'user_type': receivable_id,
                                            'parent_id': root_account.id,
                                            'company_id': root_account.company_id.id,
                                            'reconcile': True
                                        }, context=context)
                        else:
                            account_id = id_account_ids[0]

                        account = account_obj.browse(cr, SUPERUSER, account_id, context=context)
                        current_ids = property_obj.search(cr, SUPERUSER, [('name','=','property_account_receivable'),('company_id','=', account.company_id.id),('res_id','=','res.partner,%d' % partner.id)])
                        if current_ids:
                            property_obj.unlink(cr, SUPERUSER, current_ids)

                        property_obj.create(cr, SUPERUSER, {
                            'name': 'property_account_receivable',
                            'company_id': account.company_id.id,
                            'fields_id': parfield.id,
                            'res_id': 'res.partner,%d' % partner.id,
                            'type': 'many2one',
                            'value': account.id
                        })

        # Propagate changes to children if needed
        if vals.get('property_account_receivable', None):
            for partner in self.browse(cr, uid, ids, context=context):
                if partner.salesmen_ids:
                    self.write(cr, uid, [x.id for x in partner.salesmen_ids], {'property_account_receivable': vals['property_account_receivable']}, context=context)

        if vals.get('property_product_pricelist', None):
            for partner in self.browse(cr, uid, ids, context=context):
                if partner.salesmen_ids:
                    self.write(cr, uid, [x.id for x in partner.salesmen_ids], {'property_product_pricelist': vals['property_product_pricelist']}, context=context)

        return res

res_partner()