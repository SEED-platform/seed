"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from seed.landing.models import SEEDUser as User
from seed.test_helpers.fake import FakeElementFactory, FakePropertyFactory
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization


class TestElements(DeleteModelsTestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("test_user@demo.com", "test_user@demo.com", "test_pass")
        self.org, _, _ = create_organization(self.user)

        # Fake Factories
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.element_factory = FakeElementFactory(organization=self.org)

        self.property = self.property_factory.get_property()

    def test_element_assignments(self):
        """Make sure that properties can contain elements"""
        element1 = self.element_factory.get_element(property=self.property)
        element2 = self.element_factory.get_element(property=self.property)

        self.assertIn(element1, self.property.elements.all())
        self.assertIn(element2, self.property.elements.all())
