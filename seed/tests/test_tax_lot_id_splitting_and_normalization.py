from django.test import TestCase
from seed.tasks import _extract_tax_lot_ids


def make_method(value, expected):
    def run(self):
        result = _extract_tax_lot_ids(value)
        self.assertSequenceEqual(expected, result)
    return run


# Metaclass to create individual test methods per test case.
class ExtractTaxLotIDTester(type):
    def __new__(cls, name, bases, attrs):
        cases = attrs.get('cases', [])

        for doc, message, expected in cases:
            test = make_method(message, expected)
            test_name = 'test_extract_tax_lot_id_%s' % doc.lower().replace(' ', '_')
            if test_name in attrs:
                raise ValueError("Duplicate test named {0}".format(test_name))
            test.__name__ = test_name
            test.__doc__ = doc
            attrs[test_name] = test
        return super(ExtractTaxLotIDTester, cls).__new__(cls, name, bases, attrs)


class ExtractTaxLotIDTests(TestCase):
    __metaclass__ = ExtractTaxLotIDTester

    # test name, input, expected output
    cases = [
        ('single_with_hyphen', '1344-0962', ['13440962']),
        ('single_with_space', '2193 0011', ['21930011']),
        ('single_no_space', '1248F0084', ['1248F0084']),
        ('single_no_space_with_alpha', 'NNN08120459', ['NNN08120459']),
        ('double_1', '1312 0523; 1312 0524', ['13120523', '13120524']),
        ('double_2', '1534 0022;1634 0753', ['15340022', '16340753']),
        ('double_3', '1094-5001;1053-8005', ['10945001', '10538005']),
        ('double_4', '2648-0011; 5942-0057', ['26480011', '59420057']),
        ('double_5', '94624834;94624512', ['94624834', '94624512']),
        ('double_6', '12460501; NNN02460501', ['12460501', 'NNN02460501']),
        ('double_7', 'NNN 06200094;1369 0004', ['NNN06200094', '13690004']),
        ('triple_1', '33366555; 33366125; 33366148', ['33366555', '33366125', '33366148']),
        ('triple_2', '1250 0703, 1250 0755, 1250 0651', ['12500703', '12500755', '12500651']),
        ('triple_3', '50840022, 60490020', ['50840022', '60490020']),
        ('quad_1', '2219-0008, 2445-0001, 6055-0005, 2098-0003', ['22190008', '24450001', '60550005', '20980003']),
        ('compound_1', '1234-5678;9876 5432, 1048 5938', ['12345678', '98765432', '10485938']),
        # Non string values
        ('non_string_value', 123456789, ['123456789']),
        # Leading zeroes
        ('leading_zeros', '0001-1234', ['11234']),
    ]
