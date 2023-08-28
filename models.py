from odoo import tools, models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date,datetime

class ProductProduct(models.Model):
    _inherit = 'product.product'

    direct_cost = fields.Float('Direct cost')
    indirect_cost = fields.Float('Indirect cost')
    cost_ids = fields.One2many(comodel_name='product.product.cost',inverse_name='product_id',string='Costos')

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def btn_update_unit_costs(self):
        for rec in self:
            for line in rec.order_line:
                product_id = line.product_id
                product_id.standard_price = line.total_unit_cost
                product_id.indirect_cost = line.indirect_cost
                product_id.direct_cost = line.direct_cost
                cost_id = self.env['product.product.cost'].search([('order_id','=',rec.id),('product_id','=',product_id.id)])
                vals = {
                        'product_id': product_id.id,
                        'order_id': rec.id,
                        'date': str(date.today()),
                        'total_unit_cost': line.total_unit_cost,
                        'direct_cost': line.direct_cost,
                        'indirect_cost': line.indirect_cost,
                        }
                if cost_id:
                    cost_id.write(vals)
                else:
                    cost_id = self.env['product.product.cost'].create(vals)

    def _compute_exchange_rate(self):
        for rec in self:
            res = True
            if rec.currency_id.id != rec.company_id.currency_id.id:
                res = False
            rec.show_exchange_rate = res


    cost_ids = fields.One2many(comodel_name='purchase.order.cost',inverse_name='order_id',string='Facturas')
    exchange_rate = fields.Float('Tipo de cambio')
    show_exchange_rate = fields.Boolean('show_exchange_rate',compute=_compute_exchange_rate)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _compute_total_unit_cost(self):
        res = 0
        for rec in self:
            if rec.order_id.amount_untaxed == 0 \
                    or rec.order_id.state in ['sent','draft','cancel']: 
                res = 0
            elif rec.currency_id.id != self.env.ref('base.USD').id and rec.order_id.exchange_rate != 0:
                amount_invoices = 0
                for cost in rec.order_id.cost_ids:
                    invoice = cost.move_id
                    #tax_percent = cost.amount_total_currency / cost.amount_untaxed_currency
                    amount_invoices = amount_invoices + cost.amount_untaxed_currency
                percent = rec.price_subtotal / rec.order_id.amount_untaxed
                res = (( rec.price_subtotal / rec.order_id.exchange_rate ) + amount_invoices * percent) / rec.product_qty
            else:
                amount_invoices = 0
                for cost in rec.order_id.cost_ids:
                    invoice = cost.move_id
                    #tax_percent = cost.amount_total_currency / cost.amount_untaxed_currency
                    amount_invoices = amount_invoices + cost.amount_untaxed_currency
                percent = rec.price_subtotal / rec.order_id.amount_untaxed
                res = (rec.price_subtotal + amount_invoices * percent) / rec.product_qty
            rec.total_unit_cost = res
            if rec.currency_id.id == self.env.ref('base.USD'):
                rec.indirect_cost = res - (rec.price_subtotal / rec.product_qty)
                rec.direct_cost = rec.total_unit_cost - rec.indirect_cost
            else:
                exchange_rate = rec.order_id.exchange_rate or 1
                rec.indirect_cost = res - ((rec.price_subtotal / exchange_rate)/ rec.product_qty)
                rec.direct_cost = rec.total_unit_cost - rec.indirect_cost

    total_unit_cost = fields.Float('Costo total unitario',compute=_compute_total_unit_cost)
    direct_cost = fields.Float('Costo directo',compute=_compute_total_unit_cost)
    indirect_cost = fields.Float('Costo indirecto',compute=_compute_total_unit_cost)

class PurchaseOrderCost(models.Model):
    _name = 'purchase.order.cost'
    _description = 'purchase.order.cost'

    def _compute_amounts(self):
        for rec in self:
            if rec.move_line_id:
                rec.amount_total = rec.move_line_id.price_total
                rec.amount_untaxed = rec.move_line_id.price_subtotal
                if rec.exchange_rate > 0:
                    rec.amount_untaxed_currency = rec.move_line_id.price_subtotal / rec.exchange_rate
                    rec.amount_total_currency = rec.move_line_id.price_total / rec.exchange_rate
                else:
                    rec.amount_untaxed_currency = 0
                    rec.amount_total_currency = 0
            else:
                rec.amount_total = 0
                rec.amount_untaxed = 0
                rec.amount_untaxed_currency = 0

    order_id = fields.Many2one('purchase.order',string='Orden de Compra')
    move_id = fields.Many2one('account.move',string='Factura',domain=[('move_type','in',['in_invoice']),('state','=','posted')])
    move_line_id = fields.Many2one('account.move.line',string='Linea Factura')
    partner_id = fields.Many2one('res.partner',string='Proveedor',related='move_id.partner_id')
    currency_id = fields.Many2one('res.currency',string='Moneda',related='move_id.currency_id')
    percent = fields.Integer('Porcentaje', default=100)
    exchange_rate = fields.Float('Tipo de cambio')
    amount_total = fields.Float('Amount Total',compute=_compute_amounts)
    amount_untaxed = fields.Float('Amount Total',compute=_compute_amounts)
    amount_untaxed_currency = fields.Float('Amount Untaxed Currency',compute=_compute_amounts)
    amount_total_currency = fields.Float('Amount Untaxed Currency',compute=_compute_amounts)


class ProductProductCost(models.Model):
    _name = 'product.product.cost'
    _description = 'product.product.cost'

    order_id = fields.Many2one('purchase.order',string='Orden de Compra')
    product_id = fields.Many2one('product.product',string='Producto')
    date = fields.Date('Fecha',default=fields.Date.today())
    total_unit_cost = fields.Float('Costo total unitario')
    direct_cost = fields.Float('Costo directo')
    indirect_cost = fields.Float('Costo indirecto')
