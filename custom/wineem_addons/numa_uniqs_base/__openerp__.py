# -*- encoding: utf-8 -*-
#################################################################################
#
#    Copyright (C) 2011  NUMA Extreme Systems
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

{
    'name': 'Argentina: Basic country data and adaptations for UNIQS/Wineem by NUMA',
    'description': '''
                        Argentinean Localisation
                   ''',
    'category': 'Localization',
    'author': 'NUMA Extreme System',
    'website': 'http://www.numaes.com',
    'version': '8.0',
    'depends': ['base', 'sale', 'account', 'purchase', 'base_report_to_printer'],
    'data': [
        'security/ar_base_security.xml',
        'security/ir.model.access.csv',
        'afip_view.xml',
        'afip_data.xml',
        'partner_view.xml',
        'invoice_view.xml',
        'invoice_workflow.xml',
        'payment_terms.xml',
        'report/partner_ledger.xml',
        'stock_view.xml',
        'res_bank_view.xml',
        'numa_ar_base.rg830_rate.csv',
        'numa_ar_base.rg830_table.csv',
        'res.country.state.csv',
        'res.partner.title.csv',
        'sale_view.xml',
        'document_type.xml',
        'country.xml',
        'res.currency.csv',
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
