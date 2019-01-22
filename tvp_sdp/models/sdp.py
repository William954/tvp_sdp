# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Sdp(models.Model):

    _name = 'sdp'
    _description = 'Solicitud de Pago'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Referencia de la Solicitud', required=True)
    employee_id = fields.Many2one('hr.employee', string='Solicitante',default=lambda self: self.env.user.id)
    department_id = fields.Many2one('hr.department', string="Departamento")
    job_id = fields.Many2one('hr.job', string='Puesto')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Empresa')
    metodo = fields.Selection([
        ('transf', 'Transferencia'),
        ('cheque', 'Cheque'),
    ], string='Metodo', help="Metodo de pago", default='transf')
    moneda = fields.Selection([
        ('nacional', 'Nacional'),
        ('usd', 'USD'),
    ], string='Moneda', help="Moneda para pago", default='nacional')
    fecha_de_pago = fields.Date('Fecha de Pago', default=fields.Date.today,
        help="Fecha en la que se tiene que realizar el pago.")
    referencia = fields.Char('Referencia', help="No de factura u orden de pago")
    concepto = fields.Char('Concepto', help="Razon de ser del pago")
    state = fields.Selection([
        ('draft', 'New'),
        ('manager_ap', 'Vo. Bo. JD'),
        ('finanzas_ap', 'Vo. Bo. Finanzas'),
        ('vp_ap', 'Vo. Bo. VP'),
        ('planificado', 'Pago Planificado'),
        ('rechazado', 'Rechazado')
    ], string='Status',
       track_visibility='onchange', help='Estatus de la Solicitud', default='draft')
    check_ppto = fields.Selection([
        ('si_ppto', 'Presupuestado'),
        ('no_ppto', 'No Presupuestado'),
    ], string='Tipo de pago', help="Seleccione si tiene rubro de presupuesto o no lo tiene", default='si_ppto')
    proyecto = fields.Many2one('project.project',string='Nombre del Proyecto')
    clave_pro = fields.Many2one('account.analytic.account',string='Clave del Proyecto')
    rubro_cc = fields.Char('Rubro o Cuenta Contable') 
    importe = fields.Float('Importe') 
    iva = fields.Float('IVA',default='0') 
    subtotal = fields.Float('Subtotal', compute='_total') 
    retisr = fields.Float('Retención ISR') 
    retiva = fields.Float('Retención IVA') 
    total = fields.Float('Total', compute='_total') 

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id
# , group_expand='_expand_states' string='Clave')

    @api.onchange('proyecto')
    def _analitic_id(self):
        if self.proyecto:
            self.analitica = self.proyecto.analytic_account_id

    @api.one
    @api.depends('subtotal','retisr','retiva','total','iva','importe')
    def _total(self):
        self.subtotal = self.iva + self.importe
        self.total = self.subtotal - (self.retisr - self.retiva)

