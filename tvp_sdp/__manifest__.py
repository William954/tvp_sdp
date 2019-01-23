# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Solicitud de Pago',
    'version': '1.0',
    'category': 'Finanzas',
    'description': """
Agrega el módulo con formulario para solicitar pagos
=============================================================

    * Cargo a proyecto o presupuesto
    * Triple Validación
    * Finanzas, VP Y Tesorería

    """,
    'website': 'tvp.mx',
    'depends': ['base','contacts','project','account','account_accountant','hr'],
    'data': [
         'views/sdp_view.xml',
         'security/security.xml',
         'security/ir.model.access.csv'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
