from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.addons import decimal_precision as dp
from dateutil.relativedelta import relativedelta


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate property model"
    _order = "id desc"

    _sql_constraints = [
        ('check_expected_price', 'CHECK(expected_price > 0)',
         'A property expected price must be strictly positive'),
        ('check_selling_price', 'CHECK(selling_price >= 0)',
         'A property selling price must be positive'),
    ]

    name = fields.Char('Title', required=True)
    active = fields.Boolean(default=True)
    property_type_id = fields.Many2one(
        "estate.property.type", string='Property Type')
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(
        string='Available From',
        copy=False,
        default=lambda self: fields.Datetime.today() + relativedelta(months=3)
    )
    expected_price = fields.Float(
        required=True, digits=dp.get_precision('Estate price'))
    best_price = fields.Float(
        'Best offer', compute="_compute_best_price", digits=dp.get_precision('Estate price'))
    selling_price = fields.Float(
        readonly=True,
        copy=False,
        digits=dp.get_precision('Estate price')
    )
    bedrooms = fields.Integer(default=2)
    living_area = fields.Float()
    garden_area = fields.Float()
    total_area = fields.Float(compute="_compute_total_area")
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_orientation = fields.Selection(
        selection=[('north', 'North'), ('south', 'South'),
                   ('east', 'East'), ('west', 'West')]
    )
    state = fields.Selection(
        string='Status',
        required=True,
        copy=False,
        selection=[
            ('new', 'New'),
            ('of_rec', 'Offer Received'),
            ('of_acc', 'Offer Accepted'),
            ('sold', 'Sold'),
            ('canceled', 'Canceled'),
        ],
        default="new"
    )
    partner_id = fields.Many2one('res.partner', string='Buyer', copy=False)
    user_id = fields.Many2one(
        'res.users', string='Salesperson', default=lambda self: self.env.user)
    tag_ids = fields.Many2many('estate.property.tag', string='Tags')
    offer_ids = fields.One2many(
        "estate.property.offer", "property_id", string="Offers", ondelete='cascade')
    offers_count = fields.Integer('Offers count', compute="_compute_offers_data")
    offers_accepted = fields.Boolean(
        'Offers accepted', compute="_compute_offers_data")

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.garden_area + record.living_area

    @api.depends('offer_ids.price')
    def _compute_best_price(self):
        price_list = self.offer_ids.mapped('price')
        for record in self:
            if len(price_list):
                record.best_price = max(price_list)
            else:
                record.best_price = 0

    @api.depends('offer_ids')
    def _compute_offers_data(self):
        for record in self:
            record.offers_count = len(record.offer_ids)
            record.offers_accepted = any(
                state == 'accepted' for state in record.offer_ids.mapped('state'))

    @api.onchange('garden')
    def onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'north'
        else:
            self.garden_area = 0
            self.garden_orientation = ''

    def action_sold(self):
        for record in self:
            if record.state == 'canceled':
                raise UserError(_('Canceled properties cannot be sold'))
            record.state = 'sold'
        return True

    def action_cancel(self):
        for record in self:
            if record.state == 'sold':
                raise UserError(_('Sold properties cannot be canceled'))
            record.state = 'canceled'
        return True

    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):
        decimal_precision = self.env['decimal.precision'].precision_get(
            'Estate price')
        for record in self:
            price_limit = record.expected_price * 90 / 100
            if not float_is_zero(record.selling_price, precision_digits=decimal_precision):
                if float_compare(record.selling_price, price_limit, precision_digits=decimal_precision) < 0:
                    raise ValidationError(
                        _('Selling price cannot be lower than 90% of the expected price'))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_working_property(self):
        for record in self:
            if record.state in ('of_rec', 'of_acc', 'sold'):
                raise UserError(
                    _('Only new or canceled properties can be deleted'))


class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Estate property type model"
    _order = "sequence, name"

    _sql_constraints = [('type_name_unique', 'unique(name)',
                         'Property type name must be unique')]

    name = fields.Char(required=True)
    property_ids = fields.One2many(
        "estate.property", "property_type_id", string="Properties")
    sequence = fields.Integer()
    offer_ids = fields.One2many(
        "estate.property.offer", "property_type_id", string="Offers")
    offer_count = fields.Integer(compute="_compute_offer_count")

    def _compute_offer_count(self):
        for record in self:
            record.offer_count = len(record.offer_ids)


class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Estate property tag model"
    _order = "name"

    _sql_constraints = [('tag_name_unique', 'unique(name)',
                         'Property tag name must be unique')]

    name = fields.Char(required=True)
    color = fields.Integer()
