from odoo import fields, models, Command


class EstateProperty(models.Model):
    _inherit = 'estate.property'

    def action_sold(self):
        account_move = self.env['account.move'].create({
            'date': fields.Date.today(),
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Administrative fees',
                    'quantity': 1,
                    'price_unit': 100
                }),
                Command.create({
                    'name': 'Selling price tax',
                    'quantity': 1,
                    'price_unit': self.selling_price * 6/100
                }),
            ],
        })
        return super().action_sold()
