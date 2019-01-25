# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date,time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Sdp(models.Model):

    _name = 'sdp'
    _description = 'Solicitud de Pago'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    @api.model
    def create(self, vals):
        cr = self.env.cr
        cr.execute('select coalesce(max(id), 0) from "sdp"')
        id_returned = cr.fetchone()
        if (max(id_returned)+1) < 10:
            vals['name'] = "SDP000" + str(max(id_returned)+1)
        if (max(id_returned)+1) >= 10 and (max(id_returned)+1) < 100:
            vals['name'] = "SDP0" + str(max(id_returned)+1)
        if (max(id_returned)+1) >= 100 :
            vals['name'] = "SDP" + str(max(id_returned)+1)
        result = super(Sdp, self).create(vals)
        return result


    name = fields.Char('Referencia de la Solicitud', required=True,default='New')
    employee_id = fields.Many2one('hr.employee', string='Solicitante',default=lambda self: self.env.user.create_uid)
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
        ('tesoreria', 'Tesoreria'),
        ('pagado', 'Pagado'),
        ('rechazado', 'Rechazado'),
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


    jefe_directo = fields.Many2one('res.users',string='Jefe Directo')
    finanzas = fields.Many2one('res.users',string='Finanzas')
    vp_ap = fields.Many2one('res.users',string='V.P.')
    tesoreria = fields.Many2one('res.users',string='Tesoreria')
    anexos = fields.Selection([('1','Si'),('2','No')], string='Se anexan comprobantes: ')
    adjuntos = fields.Binary(string='Adjunta los anexos')

    approve_jefe_directo = fields.Char(string='Aprobacion Jefe Directo',readonly=True)
    approve_finanzas = fields.Char(string='Aprobacion Finanzas',readonly=True)
    approve_vp_ap = fields.Char(string='Aprobacion V.P.',readonly=True)
    approve_tesoreria = fields.Char(string='Aprobacion Tesoreria',readonly=True)
    refuse_user_id = fields.Char(string="Rechazado por",readonly = True,)
    refuse_date = fields.Datetime(string="Fecha de Rechazo",readonly=True)
    jefe_directo_approve_date = fields.Datetime(string='Fecha de aprobacion del Jefe Directo',readonly=True,)
    finanzas_approve_date = fields.Datetime(string='Fecha de aprobacion de Finanzas',readonly=True,)
    vp_ap_approve_date = fields.Datetime(string='Fecha de aprobacion de V.P.',readonly=True,)
    tesoreria_approve_date = fields.Datetime(string='Fecha de aprobacion de Tesoreria',readonly=True,)
    refuse_date = fields.Datetime(string="Fecha de Rechazo",readonly=True)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id

    @api.onchange('proyecto')
    def _analitic_id(self):
        if self.proyecto:
            self.analitica = self.proyecto.analytic_account_id

    @api.one
    @api.depends('subtotal','retisr','retiva','total','iva','importe')
    def _total(self):
        self.subtotal = self.iva + self.importe
        self.total = self.subtotal - (self.retisr + self.retiva)


# Aprobacion


    @api.multi
    def button_confirm(self,vals):
        for rec in self:    
            if not rec.jefe_directo:
                raise UserError(_('Porfavor selecciona un jefe directo'))
            if not rec.finanzas:
                raise UserError(_('Porfavor selecciona un encargado de finanzas'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un jefe V.P.'))
            if not rec.tesoreria:
                raise UserError(_('Porfavor selecciona un encargado de tesoreria'))
            else: 
                self.state = 'manager_ap'

 
    @api.multi
    def button_director_approval(self,vals):
        for rec in self:    
            if not rec.jefe_directo:
                raise UserError(_('Porfavor selecciona un jefe directo'))
            if not rec.finanzas:
                raise UserError(_('Porfavor selecciona un encargado de finanzas'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un jefe V.P.'))
            if not rec.tesoreria:
                raise UserError(_('Porfavor selecciona un encargado de tesoreria'))
            else: 
                rec.state = 'finanzas_ap'
                rec.approve_jefe_directo = self.env.user.name
                rec.jefe_directo_approve_date = fields.Datetime.now()

    @api.multi
    def button_finanzas_approval(self,vals):
        for rec in self:    
            if not rec.jefe_directo:
                raise UserError(_('Porfavor selecciona un jefe directo'))
            if not rec.finanzas:
                raise UserError(_('Porfavor selecciona un encargado de finanzas'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un jefe V.P.'))
            if not rec.tesoreria:
                raise UserError(_('Porfavor selecciona un encargado de tesoreria'))
            else: 
                rec.state = 'vp_ap'
                rec.approve_finanzas = self.env.user.name
                rec.finanzas_approve_date = fields.Datetime.now()


    @api.multi
    def button_vp_approval(self,vals):
        for rec in self:    
            if not rec.jefe_directo:
                raise UserError(_('Porfavor selecciona un jefe directo'))
            if not rec.finanzas:
                raise UserError(_('Porfavor selecciona un encargado de finanzas'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un jefe V.P.'))
            if not rec.tesoreria:
                raise UserError(_('Porfavor selecciona un encargado de tesoreria'))
            else: 
                rec.state = 'tesoreria'
                rec.approve_vp_ap = self.env.user.name
                rec.vp_ap_approve_date = fields.Datetime.now()

    @api.multi
    def button_tesoreria_approval(self,vals):
        for rec in self:    
            if not rec.jefe_directo:
                raise UserError(_('Porfavor selecciona un jefe directo'))
            if not rec.finanzas:
                raise UserError(_('Porfavor selecciona un encargado de finanzas'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un jefe V.P.'))
            if not rec.tesoreria:
                raise UserError(_('Porfavor selecciona un encargado de tesoreria'))
            else: 
                rec.approve_tesoreria = self.env.user.name
                rec.tesoreria_approve_date = fields.Datetime.now()


    @api.multi
    def button_cancel(self):
        self.state = 'rechazado'  
        self.refuse_user_id = self.env.user.name
        self.refuse_date = fields.Datetime.now()
   
    @api.multi
    def button_pay(self):
        self.state = 'pagado' 