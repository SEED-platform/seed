from django.test import TestCase
from seed.tasks import _normalize_address_str


class NormalizeStreetAddressTest(TestCase):
    def setUp(self):
        pass

    def test_normalize_simple_address(self):
        normalized_addr = _normalize_address_str("123 Test St.")
        self.assertEqual(normalized_addr, "hi there")
