# This file is part of the purchase_product_variant_supplier module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import datetime

from sql import Null
from sql.conditionals import Case

from trytond.model import ModelView, ModelSQL, MatchMixin, fields, \
    sequence_ordered
from trytond.pyson import Eval, If
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.modules.product import price_digits

__all__ = ['Template', 'Product', 'ProductProductSupplier', 'ProductProductSupplierPrice']


class Template:
    __metaclass__ = PoolMeta
    __name__ = 'product.template'

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        # hide product_suppliers in product template
        # uncomment next line
        # cls.product_suppliers.states['invisible'] = True


class Product:
    __metaclass__ = PoolMeta
    __name__ = 'product.product'
    purchasable_variant = fields.Function(fields.Boolean('Purchasable Variant'),
        'on_change_with_purchasable_variant', searcher='search_purchasable_variant')
    # ovewrite product_suppliers field defined at product template
    # because get_purchase_price calculate from product_suppliers field
    product_suppliers = fields.One2Many('purchase.product_product_supplier',
        'product', 'Suppliers', states={
            'invisible': (~Eval('purchasable_variant', False) |
                ~Eval('context', {}).get('company'))
            })

    @fields.depends('template')
    def on_change_with_purchasable_variant(self, name=None):
        if self.template:
            return self.template.purchasable

    @classmethod
    def search_purchasable_variant(cls, name, clause):
        return [
            ('template.purchasable',) + tuple(clause[1:]),
            ]


class ProductProductSupplier(sequence_ordered(), ModelSQL, ModelView, MatchMixin):
    'Product Variant Supplier'
    __name__ = 'purchase.product_product_supplier'
    product = fields.Many2One('product.product', 'Product', required=True,
        ondelete='CASCADE', select=True)
    party = fields.Many2One('party.party', 'Supplier', required=True,
        ondelete='CASCADE', select=True)
    name = fields.Char('Name', size=None, translate=True, select=True)
    code = fields.Char('Code', size=None, select=True)
    sequence = fields.Integer('Sequence')
    prices = fields.One2Many('purchase.product_product_supplier.price',
        'product_supplier', 'Prices')
    company = fields.Many2One('company.company', 'Company', required=True,
        ondelete='CASCADE', select=True,
        domain=[
            ('id', If(Eval('context', {}).contains('company'), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ])
    delivery_time = fields.Integer('Delivery Time', help="In number of days")
    currency = fields.Many2One('currency.currency', 'Currency', required=True,
        ondelete='RESTRICT')
    supplier_name = fields.Function(fields.Char('Supplier Name'),
        'on_change_with_supplier_name')

    @classmethod
    def __setup__(cls):
        super(ProductProductSupplier, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.id

    def get_rec_name(self, name):
        return '%s @ %s' % (self.product.rec_name, self.party.rec_name)

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
            ('product',) + tuple(clause[1:]),
            ('party',) + tuple(clause[1:]),
            ]

    @fields.depends('code', 'name', 'product')
    def on_change_with_supplier_name(self, name=None):
        if self.code and self.name:
            return '[' + self.code + '] ' + self.name
        elif self.code and not self.name:
            return '[' + self.code + '] ' + self.product.name
        elif self.name:
            return self.name
        return

    @property
    def uom(self):
        return self.product.purchase_uom

    def compute_supply_date(self, date=None):
        '''
        Compute the supply date for the Product Supplier at the given date
        '''
        Date = Pool().get('ir.date')

        if not date:
            date = Date.today()
        if self.delivery_time is None:
            return datetime.date.max
        return date + datetime.timedelta(self.delivery_time)

    def compute_purchase_date(self, date):
        '''
        Compute the purchase date for the Product Supplier at the given date
        '''
        Date = Pool().get('ir.date')

        if self.delivery_time is None:
            return Date.today()
        return date - datetime.timedelta(self.delivery_time)

    @staticmethod
    def get_pattern():
        context = Transaction().context
        return {
            'party': context.get('supplier'),
            }


class ProductProductSupplierPrice(sequence_ordered(), ModelSQL, ModelView, MatchMixin):
    'Product Variant Supplier Price'
    __name__ = 'purchase.product_product_supplier.price'
    product_supplier = fields.Many2One('purchase.product_product_supplier',
        'Supplier', required=True, ondelete='CASCADE')
    quantity = fields.Float('Quantity', required=True, help='Minimal quantity')
    unit_price = fields.Numeric('Unit Price', required=True,
        digits=price_digits)
    sequence = fields.Integer('Sequence')

    @classmethod
    def __setup__(cls):
        super(ProductProductSupplierPrice, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @staticmethod
    def order_sequence(tables):
        table, _ = tables[None]
        return [Case((table.sequence == Null, 0), else_=1), table.sequence]

    @staticmethod
    def default_quantity():
        return 0.0

    @staticmethod
    def get_pattern():
        return {}

    def match(self, quantity, uom, pattern):
        pool = Pool()
        Uom = pool.get('product.uom')
        test_quantity = Uom.compute_qty(
            self.product_supplier.uom, self.quantity, uom)
        if test_quantity > quantity:
            return False
        return super(ProductProductSupplierPrice, self).match(pattern)
