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


    name = fields.Char('Referencia de la Solicitud', required=True,default='New',track_visibility=True, readonly=True)
    employee_id = fields.Many2one('res.users', string='Solicitante',default=lambda self: self.env.user,track_visibility=True)
    department_id = fields.Many2one('hr.department', string="Departamento",track_visibility=True)
    job_id = fields.Many2one('hr.job', string='Puesto',track_visibility=True)
    active = fields.Boolean(default=True,track_visibility=True)
    company_id = fields.Many2one('res.company', string='Empresa',track_visibility=True)
    metodo = fields.Selection([
        ('transf', 'Transferencia'),
        ('cheque', 'Cheque'),
    ], string='Metodo', help="Metodo de pago", default='transf',track_visibility=True)
    moneda = fields.Selection([
        ('nacional', 'Nacional'),
        ('usd', 'USD'),
    ], string='Moneda', help="Moneda para pago", default='nacional',track_visibility=True)
    fecha_de_pago = fields.Date('Fecha de Pago', default=fields.Date.today,
        help="Fecha en la que se tiene que realizar el pago.",track_visibility=True)
    referencia = fields.Char('Referencia', help="No de factura u orden de pago",track_visibility=True)
    concepto = fields.Char('Concepto', help="Razon de ser del pago",track_visibility=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('manager_ap', 'Aprobacion Jefe Directo'),
        ('finanzas_ap', 'Aprobacion Vo. Bo.1'),
        ('vp_ap', 'Aprobacion Vo. Bo.2'),
        ('tesoreria', 'Aprobacion Tesoreria'),
        ('pagado', 'Pagado'),
        ('rechazado', 'Rechazado'),
    ], string='Status',
       track_visibility='onchange', help='Estatus de la Solicitud', default='draft')


    check_ppto = fields.Selection([
        ('si_ppto', 'Presupuestado'),
        ('no_ppto', 'No Presupuestado'),
    ], string='Tipo de pago', help="Seleccione si tiene rubro de presupuesto o no lo tiene", default='si_ppto',track_visibility=True)
    proyecto = fields.Many2one('project.project',string='Nombre del Proyecto',track_visibility=True)
    clave_pro = fields.Many2one('account.analytic.account',string='Clave del Proyecto',track_visibility=True)
    rubro_cc = fields.Char('Rubro o Cuenta Contable',track_visibility=True)
    importe = fields.Float('Importe',track_visibility=True)
    iva = fields.Float('IVA',default='0',track_visibility=True)
    subtotal = fields.Float('Subtotal', compute='_total',onchange_visibility=True)
    retisr = fields.Float('Retención ISR',track_visibility=True)
    retiva = fields.Float('Retención IVA',track_visibility=True)
    total = fields.Float('Total', compute='_total',onchage_visibility=True)


    jefe_directo = fields.Many2one('res.users',string='Jefe Directo',track_visibility=True)
    finanzas = fields.Many2one('res.users',string='Aprobador Vo. Bo.1',track_visibility=True)
    vp_ap = fields.Many2one('res.users',string='Aprobador Vo. Bo.2',track_visibility=True)
    tesoreria = fields.Many2one('res.users',string='Tesoreria',track_visibility=True)
    anexos = fields.Selection([('1','Si'),('2','No')], string='Se anexan comprobantes: ',track_visibility=True)
    adjuntos = fields.Binary(string='Adjunta los anexos',track_visibility=True)

    approve_jefe_directo = fields.Char(string='Aprobacion Jefe Directo',readonly=True,track_visibility=True)
    approve_finanzas = fields.Char(string='Aprobacion Vo. Bo.1',readonly=True,track_visibility=True)
    approve_vp_ap = fields.Char(string='Aprobacion Vo. Bo.2',readonly=True,track_visibility=True)
    approve_tesoreria = fields.Char(string='Aprobacion Tesoreria',readonly=True,track_visibility=True)
    refuse_user_id = fields.Char(string="Rechazado por",readonly = True,track_visibility=True)
    refuse_date = fields.Datetime(string="Fecha de Rechazo",readonly=True,track_visibility=True)
    jefe_directo_approve_date = fields.Datetime(string='Fecha de aprobacion del Jefe Directo',readonly=True,track_visibility=True)
    finanzas_approve_date = fields.Datetime(string='Fecha de aprobacion Vo. Bo.1',readonly=True,track_visibility=True)
    vp_ap_approve_date = fields.Datetime(string='Fecha de aprobacion de Vo. Bo.2',readonly=True,track_visibility=True)
    tesoreria_approve_date = fields.Datetime(string='Fecha de aprobacion de Tesoreria',readonly=True,track_visibility=True)
    refuse_date = fields.Datetime(string="Fecha de Rechazo",readonly=True,track_visibility=True)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id

    @api.onchange('proyecto')
    def _analitic_id(self):
        if self.proyecto:
            self.clave_pro = self.proyecto.analytic_account_id

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
                raise UserError(_('Porfavor selecciona un Vo. Bo.1'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un Vo. Bo.2'))
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
                raise UserError(_('Porfavor selecciona un  Vo. Bo.1'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un  Vo. Bo.2'))
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
                raise UserError(_('Porfavor selecciona un  Vo. Bo.1'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un  Vo. Bo.2'))
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
                raise UserError(_('Porfavor selecciona un  Vo. Bo.1'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un  Vo. Bo.2'))
            if not rec.tesoreria:
                raise UserError(_('Porfavor selecciona un encargado de tesoreria'))
            else: 
                rec.state = 'tesoreria'
                rec.approve_vp_ap = self.env.user.name
                rec.vp_ap_approve_date = fields.Datetime.now()

    @api.multi
    def button_pay(self,vals):
        for rec in self:    
            if not rec.jefe_directo:
                raise UserError(_('Porfavor selecciona un jefe directo'))
            if not rec.finanzas:
                raise UserError(_('Porfavor selecciona un  Vo. Bo.1'))
            if not rec.vp_ap:
                raise UserError(_('Porfavor selecciona un  Vo. Bo.2'))
            if not rec.tesoreria:
                raise UserError(_('Porfavor selecciona un encargado de tesoreria'))
            else: 
                rec.approve_tesoreria = self.env.user.name
                rec.tesoreria_approve_date = fields.Datetime.now()
                self.state = 'pagado' 


    @api.multi
    def button_cancel(self):
        self.state = 'rechazado'  
        self.refuse_user_id = self.env.user.name
        self.refuse_date = fields.Datetime.now()
   
