from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    iterated = fields.Boolean(string='Iterated', default=False, help='Check this if the quotation has been iterated')
