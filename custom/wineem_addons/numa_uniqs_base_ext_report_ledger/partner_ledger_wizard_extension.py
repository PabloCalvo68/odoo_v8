# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import time


from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import netsvc

import base64
from xlrd import open_workbook
import StringIO

import pdb
import logging


logger = logging.getLogger(__name__)

class partner_ledger_wizard_ext_fecha_vencimiento(osv.osv_memory):
    """
    """
    _name = 'numa_ar_base.partner_ledger_wizard'
    _inherit = 'numa_ar_base.partner_ledger_wizard' 
    
    
    def action_report_con_fecha_vencimiento(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        plw = self.browse(cr, uid, ids[0], context=context)

        partner_ids = context.get('active_ids', 
                                  ('active_id' in context) and [context['active_id']] or [])
        
        data = {}
        data['ids'] = ids
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = {}
        data['form']['partner_ids'] = partner_ids
        data['form']['fiscalyear_ids'] = [f.id for f in plw.fiscalyear_ids]
        data['form']['start_date'] = plw.start_date
        data['form']['reconcil'] = plw.reconcil
        data['form']['docs_on_maturity'] = plw.docs_on_maturity
        data['form']['include_docs'] = plw.include_docs
        data['form']['include_children'] = plw.include_children
        data['form']['result_selection'] = plw.result_selection
        
        return {
                'type': 'ir.actions.report.xml',
                'report_name': 'partner_ledger_wizard_con_fecha_vencimiento',
                'datas': data,
        }
        
partner_ledger_wizard_ext_fecha_vencimiento()
