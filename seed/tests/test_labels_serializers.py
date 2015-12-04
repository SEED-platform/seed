"""
Unit tests for map.py
"""
__author__ = 'Piper Merriam <pipermerriam@gmail.com>'
__date__ = '2015/12/04'

from django.test import TestCase

from seed.lib.superperms.orgs.models import (
    Organization as SuperOrganization,
)
from seed.models import (
    BuildingSnapshot,
    StatusLabel as Label,
    CanonicalBuilding,
)
from seed.landing.models import SEEDUser
from seed.serializers.labels import (
    LabelSerializer,
    UpdateBuildingLabelsSerializer,
)

from seed.factory import SEEDFactory


def UserFactory(is_superuser=False, **kwargs):
    """
    Small helper function fro creating users
    """
    idx = SEEDUser.objects.count() + 1
    if 'username' not in kwargs:
        kwargs['username'] = "test-user-{0}".format(idx)
    if 'email' not in kwargs:
        kwargs['email'] = "test-user-{0}@example.com".format(idx)
    if 'password' not in kwargs:
        kwargs['password'] = "test-password"

    if is_superuser:
        user = SEEDUser.objects.create_superuser(**kwargs)
    else:
        user = SEEDUser.objects.create_user(**kwargs)

    return user


class TestLabelSerializer(TestCase):
    """Test the label serializer"""

    def test_initialization_requires_organization_as_argument(self):
        with self.assertRaises(KeyError):
            LabelSerializer()

        organization = SuperOrganization.objects.create(name='test-org')
        LabelSerializer(super_organization=organization)

    def test_uses_provided_organization_over_post_data(self):
        """
        Checks that the serializer doesn't trust a user-provided super
        organization, but rather uses the one determined by the server to
        belong to the user.
        """
        organization_a = SuperOrganization.objects.create(name='test-org-a')
        organization_b = SuperOrganization.objects.create(name='test-org-b')

        data = {
            "name": "test-label-1",
            "color": "red",
            "organization_id": organization_a.pk,
        }
        serializer = LabelSerializer(data=data, super_organization=organization_b)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data['super_organization'], organization_b
        )


class TestUpdateBuildingLabelsSerializer(TestCase):
    def test_initialization_requires_organization_as_argument(self):
        with self.assertRaises(KeyError):
            UpdateBuildingLabelsSerializer(
                queryset=BuildingSnapshot.objects.none(),
            )

        organization = SuperOrganization.objects.create(name='test-org')
        UpdateBuildingLabelsSerializer(
            queryset=BuildingSnapshot.objects.none(),
            super_organization=organization,
        )

    def test_initialization_requires_queryset_as_argument(self):
        organization = SuperOrganization.objects.create(name='test-org')

        with self.assertRaises(KeyError):
            UpdateBuildingLabelsSerializer(
                super_organization=organization,
            )

        UpdateBuildingLabelsSerializer(
            super_organization=organization,
            queryset=BuildingSnapshot.objects.none(),
        )

    def test_updates_all_buildings_when_all_checkbox_true(self):
        SEEDFactory.building_snapshot()
        SEEDFactory.building_snapshot()

        qs = BuildingSnapshot.objects.all()
        self.assertEqual(qs.count(), 2)

        organization = SuperOrganization.objects.create(name='test-org')
        data = {
            'add_label_ids': [],
            'remove_label_ids': [],
            'selected_buildings': [],
            'select_all_checkbox': True,
        }

        serializer = UpdateBuildingLabelsSerializer(
            data=data,
            super_organization=organization,
            queryset=qs,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        updated_qs = serializer.save()
        self.assertSequenceEqual(
            tuple(qs),
            tuple(updated_qs),
        )

    def test_updates_only_provided_buildings_when_ids_passed_in(self):
        bs_1 = SEEDFactory.building_snapshot()
        bs_2 = SEEDFactory.building_snapshot()

        qs = BuildingSnapshot.objects.all()
        self.assertEqual(qs.count(), 2)

        organization = SuperOrganization.objects.create(name='test-org')
        data = {
            'add_label_ids': [],
            'remove_label_ids': [],
            'selected_buildings': [bs_1.pk],
            'select_all_checkbox': False,
        }

        serializer = UpdateBuildingLabelsSerializer(
            data=data,
            super_organization=organization,
            queryset=qs,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        updated_qs = serializer.save()
        self.assertIn(bs_1, updated_qs)
        self.assertNotIn(bs_2, updated_qs)

    def test_labels_are_applied(self):
        organization = SuperOrganization.objects.create(name='test-org')

        label_a = Label.objects.create(
            color="red",
            name="label-a",
            super_organization=organization,
        )
        label_b = Label.objects.create(
            color="red",
            name="label-b",
            super_organization=organization,
        )

        bs_1 = SEEDFactory.building_snapshot(
            canonical_building=CanonicalBuilding.objects.create(),
        )
        bs_2 = SEEDFactory.building_snapshot(
            canonical_building=CanonicalBuilding.objects.create(),
        )

        self.assertFalse(bs_1.canonical_building.labels.filter(pk=label_a.pk).exists())
        self.assertFalse(bs_1.canonical_building.labels.filter(pk=label_b.pk).exists())
        self.assertFalse(bs_2.canonical_building.labels.filter(pk=label_a.pk).exists())
        self.assertFalse(bs_2.canonical_building.labels.filter(pk=label_b.pk).exists())

        qs = BuildingSnapshot.objects.all()
        self.assertEqual(qs.count(), 2)

        data = {
            'add_label_ids': [label_a.pk, label_b.pk],
            'remove_label_ids': [],
            'selected_buildings': [],
            'select_all_checkbox': True,
        }

        serializer = UpdateBuildingLabelsSerializer(
            data=data,
            super_organization=organization,
            queryset=qs,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        serializer.save()
        self.assertEqual(qs.count(), 2)

        self.assertTrue(bs_1.canonical_building.labels.filter(pk=label_a.pk).exists())
        self.assertTrue(bs_1.canonical_building.labels.filter(pk=label_b.pk).exists())
        self.assertTrue(bs_2.canonical_building.labels.filter(pk=label_a.pk).exists())
        self.assertTrue(bs_2.canonical_building.labels.filter(pk=label_b.pk).exists())

    def test_labels_are_removed(self):
        organization = SuperOrganization.objects.create(name='test-org')

        label_a = Label.objects.create(
            color="red",
            name="label-a",
            super_organization=organization,
        )
        label_b = Label.objects.create(
            color="red",
            name="label-b",
            super_organization=organization,
        )

        bs_1 = SEEDFactory.building_snapshot(
            canonical_building=CanonicalBuilding.objects.create(),
        )
        bs_2 = SEEDFactory.building_snapshot(
            canonical_building=CanonicalBuilding.objects.create(),
        )

        bs_1.canonical_building.labels.add(label_a, label_b)
        bs_2.canonical_building.labels.add(label_b)

        # Sanity check
        self.assertTrue(bs_1.canonical_building.labels.filter(pk=label_a.pk).exists())
        self.assertTrue(bs_1.canonical_building.labels.filter(pk=label_b.pk).exists())
        self.assertFalse(bs_2.canonical_building.labels.filter(pk=label_a.pk).exists())
        self.assertTrue(bs_2.canonical_building.labels.filter(pk=label_b.pk).exists())

        qs = BuildingSnapshot.objects.all()
        self.assertEqual(qs.count(), 2)

        data = {
            'add_label_ids': [],
            'remove_label_ids': [label_a.pk, label_b.pk],
            'selected_buildings': [],
            'select_all_checkbox': True,
        }

        serializer = UpdateBuildingLabelsSerializer(
            data=data,
            super_organization=organization,
            queryset=qs,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        serializer.save()
        self.assertEqual(qs.count(), 2)

        self.assertFalse(bs_1.canonical_building.labels.filter(pk=label_a.pk).exists())
        self.assertFalse(bs_1.canonical_building.labels.filter(pk=label_b.pk).exists())
        self.assertFalse(bs_2.canonical_building.labels.filter(pk=label_a.pk).exists())
        self.assertFalse(bs_2.canonical_building.labels.filter(pk=label_b.pk).exists())
