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


{
        "name" : "Account voucher for Wineem - UNIQS",
        "version" : "1.0",
        "author" : "NUMA Extreme Systems",
        "website" : "www.numaes.com",
        "category" : "Vertical Modules/Parametrization",
        "description": """Wineem Account voucher""",
        "depends" : ["base", "account", "account_voucher"],
        "init_xml" : [ ],
        "demo_xml" : [ ],
        "update_xml" : [
            "security/security.xml",
            "security/ir.model.access.csv",
            "voucher_view.xml", 
        ],
        "installable": True,
        "active": False,
} 
