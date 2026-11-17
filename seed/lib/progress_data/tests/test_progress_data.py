"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

import pytest
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.progress_data.progress_data import ProgressData
from seed.utils.organizations import create_organization

logger = logging.getLogger(__name__)


class TestProgressData(TestCase):
    """Tests that our logic for constructing cleaners works."""

    def setUp(self):
        pass

    def test_create_progress(self):
        pd = ProgressData(func_name="test_func", unique_id="abc123")

        self.assertEqual(pd.key, ":1:SEED:test_func:PROG:abc123")

        data_eql = {
            "status": "not-started",
            "status_message": "",
            "summary": None,
            "stacktrace": None,
            "func_name": "test_func",
            "progress_key": ":1:SEED:test_func:PROG:abc123",
            "progress": 0,
            "message": None,
            "total": None,
            "unique_id": "abc123",
        }
        self.assertEqual(pd.data["status"], "not-started")
        self.assertDictEqual(pd.data, data_eql)
        self.assertEqual(pd.total, None)

    def test_total_progress(self):
        pd = ProgressData(func_name="test_func_2", unique_id="def456")
        pd.total = 10
        self.assertEqual(pd.increment_value(), 10)

    def test_init_by_data(self):
        pd = ProgressData(func_name="test_func_3", unique_id="ghi789")
        pd.total = 100
        self.assertEqual(pd.key, ":1:SEED:test_func_3:PROG:ghi789")

        pd2 = ProgressData.from_key(pd.key)
        self.assertDictEqual(pd.data, pd2.data)

    def test_key_missing(self):
        with pytest.raises(Exception) as e:  # noqa: PT011
            ProgressData.from_key("some_random_key")
        self.assertEqual(str(e.value), "Could not find key some_random_key in cache")

    def test_delete_cache(self):
        pd = ProgressData(func_name="test_func_4", unique_id="1q2w3e")
        pd.total = 525600
        pd.data["status"] = "doing-something"
        pd.save()

        self.assertEqual(pd.result()["total"], 525600)
        self.assertEqual(pd.data["status"], "doing-something")
        self.assertEqual(pd.delete()["total"], None)

    def test_status_message(self):
        pd = ProgressData(func_name="test_func_5", unique_id="plokij")
        pd.total = 42
        pd.step("Stepping")

        self.assertEqual(pd.result()["total"], 42)
        self.assertEqual(pd.result()["status_message"], "Stepping")

        # if we call step again, then the status message should not change
        pd.step()
        self.assertEqual(pd.result()["status_message"], "Stepping")

        # Now passing in empty string will reset
        pd.step("")
        self.assertEqual(pd.result()["status_message"], "")

    def test_summary(self):
        pd = ProgressData(func_name="test_func_6", unique_id="pokemon")
        self.assertIsNone(pd.summary())

        new_summary = {"Values": ["As", "A", "List"]}
        pd.update_summary(new_summary)
        self.assertEqual(pd.summary(), new_summary)

        pd.step(new_summary=4815162342)
        self.assertEqual(pd.summary(), 4815162342)

    def test_tags(self):
        pd = ProgressData(func_name="test_func_7", unique_id="tagged", organization_id=1, access_level_instance_id=2)
        self.assertEqual((pd.data["organization_id"], pd.data["access_level_instance_id"]), (1, 2))

        # the tags are kept by progress data read from the cache, and when it is saved, deleted (which reinitializes it),
        # stepped, and finished
        pd2 = ProgressData.from_key(pd.key)
        self.assertEqual((pd2.organization_id, pd2.access_level_instance_id), (1, 2))
        pd2.total = 2
        pd2.save()
        pd2.delete()
        pd2.step("Stepping", new_summary={"Values": ["A"]})
        pd2.add_file_info("file.xml", {"warnings": []})
        pd2.finish_with_error("Error", "Traceback")

        pd.load()
        for data in (pd.data, ProgressData.from_key(pd.key).result()):
            self.assertEqual((data["organization_id"], data["access_level_instance_id"]), (1, 2))
            self.assertEqual(data["status"], "error")

    def test_tags_are_optional(self):
        # e.g., the progress of a task that is not limited to an access level instance
        pd = ProgressData(func_name="test_func_8", unique_id="organization", organization_id=1)
        self.assertEqual(pd.data["organization_id"], 1)
        self.assertNotIn("access_level_instance_id", pd.data)

        pd = ProgressData(func_name="test_func_8", unique_id="untagged")
        self.assertNotIn("organization_id", ProgressData.from_key(pd.key).data)

    def test_untag(self):
        pd = ProgressData(func_name="test_func_9", unique_id="untag", organization_id=1, access_level_instance_id=2)
        pd.untag()
        pd.finish_with_success()

        data = ProgressData.from_key(pd.key).data
        self.assertNotIn("organization_id", data)
        self.assertNotIn("access_level_instance_id", data)
        self.assertEqual(data["status"], "success")

    def test_for_organization(self):
        user = User.objects.create_user(username="test_user@demo.com", password="test_pass")
        org, _, _ = create_organization(user)

        pd = ProgressData.for_organization("test_func_10", "organization", org.id)
        self.assertEqual((pd.data["organization_id"], pd.data["access_level_instance_id"]), (org.id, org.root.id))
