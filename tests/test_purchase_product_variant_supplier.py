# This file is part purchase_product_variant_supplier module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
import doctest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import doctest_teardown, doctest_checker

class PurchaseProductVariantSupplierTestCase(ModuleTestCase):
    'Test Purchase Product Variant Supplier module'
    module = 'purchase_product_variant_supplier'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        PurchaseProductVariantSupplierTestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_purchase_product_variant_supplier.rst',
            tearDown=doctest_teardown, encoding='UTF-8',
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE,
            checker=doctest_checker))
    return suite
