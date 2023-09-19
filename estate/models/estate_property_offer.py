from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.addons import decimal_precision as dp
from dateutil.relativedelta import relativedelta


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate property offer model"
    _order = "price desc"

    _sql_constraints = [
        ('check_price', 'CHECK(price > 0)',
         'A property expected price must be strictly positive'),
    ]

    price = fields.Float()
    state = fields.Selection(
        selection=[('accepted', 'Accepted'), ('refused', 'Refused')],
        copy=False
    )
    partner_id = fields.Many2one('res.partner', required=True)
    property_id = fields.Many2one('estate.property', required=True)
    property_type_id = fields.Many2one(
        'estate.property.type', related="property_id.property_type_id", store=True)
    validity = fields.Integer(default=7)
    date_deadline = fields.Date(
        compute='_compute_date_deadline', inverse='_inverse_validity')

    @api.depends('validity')
    def _compute_date_deadline(self):
        for record in self:
            if record.create_date:
                record.date_deadline = record.create_date + \
                    relativedelta(days=record.validity)

    def _inverse_validity(self):
        for record in self:
            if record.create_date and record.date_deadline:
                delta = record.date_deadline - record.create_date.date()
                record.validity = delta.days

    def action_accept(self):
        for record in self:
            if not any(state == 'accepted' for state in record.property_id.offer_ids.mapped('state')):
                record.state = 'accepted'
                record.property_id.partner_id = record.partner_id
                record.property_id.selling_price = record.price
                record.property_id.state = 'of_acc'
        return True

    def action_refuse(self):
        for record in self:
            record.state = 'refused'
        return True

    @api.model
    def create(self, vals):
        estate_property_obj = self.env['estate.property'].browse(
            vals['property_id'])
        decimal_precision = self.env['decimal.precision'].precision_get(
            'Estate price')
        offer_price_list = estate_property_obj.offer_ids.mapped('price')
        if len(offer_price_list):
            max_price_offer = max(offer_price_list)
            if float_compare(vals['price'], max_price_offer, precision_digits=decimal_precision) < 0:
                raise UserError(
                    _('The offer must be higher than {:.{}f}'.format(max_price_offer, decimal_precision)))
        estate_property_obj.state = 'of_rec'
        return super().create(vals)
