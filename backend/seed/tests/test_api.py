"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import base64
import json
from datetime import date
from unittest import mock

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse_lazy
from rest_framework_simplejwt.tokens import AccessToken

from seed.authentication import AUTHENTICATE_HEADER
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Column, Cycle
from seed.serializers.columns import ColumnSerializer
from seed.utils.api import get_api_endpoints
from seed.utils.organizations import create_organization


class SchemaGenerationTests(TestCase):
    def test_get_api_endpoints_utils(self):
        """
        Test of function that traverses all URLs looking for api endpoints.
        """
        res = get_api_endpoints()
        for url, fn in res.items():
            self.assertTrue(fn.is_api_endpoint)
            self.assertTrue(url.startswith("/"))


class TestApi(TestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",  # the username needs to be in the form of an email.
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Jaqen",
            "last_name": "H'ghar",
        }
        self.user = User.objects.create_user(**user_details)
        self.user.generate_key()
        self.org, _, _ = create_organization(self.user)
        self.default_cycle = Cycle.objects.filter(organization_id=self.org).first()
        self.cycle, _ = Cycle.objects.get_or_create(
            name="Test Hack Cycle 2015",
            organization=self.org,
            start=date(2015, 1, 1),
            end=date(2015, 12, 31),
        )
        auth_string = base64.urlsafe_b64encode(bytes(f"{self.user.username}:{self.user.api_key}", "utf-8"))
        self.auth_string = f"Basic {auth_string.decode('utf-8')}"
        self.headers = {"Authorization": self.auth_string}

        self.default_reports_x_axis_options = Column.objects.filter(organization=self.org, table_name="PropertyState").order_by("id")[0:3]
        for c in self.default_reports_x_axis_options:
            c.is_option_for_reports_x_axis = True
            c.save()

        self.default_reports_y_axis_options = Column.objects.filter(organization=self.org, table_name="PropertyState").order_by("id")[3:6]
        for c in self.default_reports_y_axis_options:
            c.is_option_for_reports_y_axis = True
            c.save()

    def get_org_id(self, response, username):
        """Return the org id from the passed dictionary and username"""
        org_id = None
        for ctr in range(len(response["organizations"])):
            if response["organizations"][ctr]["owners"][0]["email"] == username:
                org_id = response["organizations"][ctr]["org_id"]
                break

        return org_id

    def test_user_profile(self):
        # test logging in with the password, the remaining versions will use the HTTP Authentication
        self.client.login(username="test_user@demo.com", password="test_pass")
        r = self.client.get("/api/v3/users/" + str(self.user.pk) + "/", follow=True)
        self.assertEqual(r.status_code, 200)

        r = json.loads(r.content)
        self.assertEqual(r["first_name"], "Jaqen")
        self.assertEqual(r["last_name"], "H'ghar")
        self.client.logout()

    def test_with_http_authorization(self):
        r = self.client.get(f"/api/v3/users/{self.user.pk!s}/", follow=True, data={}, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertNotEqual(r, None)

    def test_organization(self):
        self.client.login(username="test_user@demo.com", password="test_pass")
        r = self.client.get("/api/v3/organizations/", follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        # {
        #     "organizations": [{
        #           "is_parent": true,
        #           "user_role": "owner",
        #           "sub_orgs": [],
        #           "number_of_users": 1,
        #           "id": 1,
        #           "owners": [
        #               {
        #                   "first_name": "Jaqen",
        #                   "last_name": "H'ghar",
        #                   "email": "test_user@demo.com",
        #                   "id": 1
        #               }
        #           ],
        #           "name": "",
        #           "created": "2016-09-16",
        #           "org_id": 1,
        #           "user_is_owner": true,
        #           "parent_id": 1,
        #           "cycles": []
        #           }]
        # }
        r = json.loads(r.content)
        self.assertEqual(len(r["organizations"]), 1)
        self.assertEqual(len(r["organizations"][0]["sub_orgs"]), 0)
        # Num buildings is no longer valid. The count of properties are in the cycle
        # self.assertEqual(r['organizations'][0]['num_buildings'], 0)
        self.assertEqual(len(r["organizations"][0]["owners"]), 1)
        self.assertEqual(r["organizations"][0]["number_of_users"], 1)
        self.assertEqual(r["organizations"][0]["user_role"], "owner")
        self.assertEqual(r["organizations"][0]["owners"][0]["first_name"], "Jaqen")
        self.assertEqual(
            r["organizations"][0]["cycles"],
            [
                {
                    "name": str(date.today().year - 1) + " Calendar Year",
                    "num_properties": 0,
                    "num_taxlots": 0,
                    "cycle_id": self.default_cycle.pk,
                },
                {
                    "name": "Test Hack Cycle 2015",
                    "num_properties": 0,
                    "num_taxlots": 0,
                    "cycle_id": self.cycle.pk,
                },
            ],
        )

    def test_organization_details(self):
        r = self.client.get("/api/v3/organizations/", follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        # get details on the organization
        r = self.client.get("/api/v3/organizations/" + str(organization_id) + "/", follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)

        # {
        #     "status": "success",
        #     "organization": {
        #         "sub_orgs": [],
        #         "num_buildings": 0,
        #         "owners": [
        #             {
        #                 "first_name": "Jaqen",
        #                 "last_name": "H'ghar",
        #                 "email": "test_user@demo.com",
        #                 "id": 2
        #             }
        #         ],
        #         "number_of_users": 1,
        #         "name": "",
        #         "user_role": "owner",
        #         "is_parent": true,
        #         "org_id": 2,
        #         "id": 2,
        #         "user_is_owner": true
        #     }
        # }

        r = json.loads(r.content)
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["organization"]["number_of_users"], 1)
        self.assertEqual(len(r["organization"]["owners"]), 1)
        self.assertEqual(r["organization"]["user_is_owner"], True)
        # dict order can vary
        rx = sorted(r["organization"]["default_reports_x_axis_options"], key=lambda x: x["id"])
        ry = sorted(r["organization"]["default_reports_y_axis_options"], key=lambda x: x["id"])
        cx = sorted([dict(x) for x in ColumnSerializer(self.default_reports_x_axis_options, many=True).data], key=lambda y: y["id"])
        cy = sorted([dict(x) for x in ColumnSerializer(self.default_reports_y_axis_options, many=True).data], key=lambda y: y["id"])

        self.assertEqual(rx, cx)
        self.assertEqual(ry, cy)

    def test_set_default_reports_axis_options(self):
        # assert old axis set
        self.assertTrue(all(c.is_option_for_reports_x_axis for c in self.default_reports_x_axis_options))
        self.assertTrue(all(c.is_option_for_reports_y_axis for c in self.default_reports_y_axis_options))

        r = self.client.get("/api/v3/organizations/" + str(self.org.id) + "/", follow=True, **self.headers)
        r = json.loads(r.content)

        self.assertEqual(
            r["organization"]["default_reports_x_axis_options"], ColumnSerializer(self.default_reports_x_axis_options, many=True).data
        )
        self.assertEqual(
            r["organization"]["default_reports_y_axis_options"], ColumnSerializer(self.default_reports_y_axis_options, many=True).data
        )

        # change axis
        new_default_reports_x_axis_options = Column.objects.filter(organization=self.org, table_name="PropertyState").order_by("id")[10:13]
        new_default_reports_y_axis_options = Column.objects.filter(organization=self.org, table_name="PropertyState").order_by("id")[13:16]

        url = reverse_lazy("api:v3:organizations-save-settings", args=[self.org.id]) + f"?organization_id={self.org.id}"
        res = self.client.put(
            url,
            data=json.dumps(
                {
                    "organization": {
                        "default_reports_x_axis_options": [c.id for c in new_default_reports_x_axis_options],
                        "default_reports_y_axis_options": [c.id for c in new_default_reports_y_axis_options],
                    }
                }
            ),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(res.status_code, 200)

        # check the axis changed
        r = self.client.get("/api/v3/organizations/" + str(self.org.id) + "/", follow=True, **self.headers)
        r = json.loads(r.content)
        self.assertEqual(
            r["organization"]["default_reports_x_axis_options"],
            [dict(d) for d in ColumnSerializer(new_default_reports_x_axis_options, many=True).data],
        )
        self.assertEqual(
            r["organization"]["default_reports_y_axis_options"],
            [dict(d) for d in ColumnSerializer(new_default_reports_y_axis_options, many=True).data],
        )

        self.assertFalse(
            any(c.is_option_for_reports_x_axis for c in Column.objects.filter(id__in=[c.id for c in self.default_reports_x_axis_options]))
        )
        self.assertFalse(
            any(c.is_option_for_reports_y_axis for c in Column.objects.filter(id__in=[c.id for c in self.default_reports_y_axis_options]))
        )
        self.assertTrue(
            all(c.is_option_for_reports_x_axis for c in Column.objects.filter(id__in=[c.id for c in new_default_reports_x_axis_options]))
        )
        self.assertTrue(
            all(c.is_option_for_reports_y_axis for c in Column.objects.filter(id__in=[c.id for c in new_default_reports_y_axis_options]))
        )

    def test_csrf_enforced_for_session_but_not_api_key(self):
        # The ineffective APIBypassCSRFMiddleware was removed (#5326); DRF handles CSRF per authentication class
        self.assertNotIn("seed.utils.api.APIBypassCSRFMiddleware", settings.MIDDLEWARE)

        url = f"/api/v3/users/{self.user.pk}/"
        user_payload = json.dumps({"first_name": "Arya", "last_name": "Stark", "email": self.user.username})

        # API key clients do not need a CSRF token
        api_client = Client(enforce_csrf_checks=True)
        r = api_client.put(url, data=user_payload, content_type="application/json", **self.headers)
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Arya")

        # Session-authenticated clients without a CSRF token are rejected
        session_client = Client(enforce_csrf_checks=True)
        session_client.login(username="test_user@demo.com", password="test_pass")
        session_payload = json.dumps({"first_name": "Sansa", "last_name": "Stark", "email": self.user.username})
        r = session_client.put(url, data=session_payload, content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("CSRF", r.json()["detail"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Arya")

    def test_update_user(self):
        user_payload = {"first_name": "Arya", "last_name": "Stark", "email": self.user.username}
        r = self.client.put(
            f"/api/v3/users/{self.user.pk}/", data=json.dumps(user_payload), content_type="application/json", **self.headers
        )

        # re-retrieve the user profile
        res = self.client.get("/api/v3/users/" + str(self.user.pk) + "/", follow=True, **self.headers)
        r = json.loads(res.content)

        self.assertEqual(res.status_code, 200)

        self.assertEqual(r["first_name"], "Arya")
        self.assertEqual(r["last_name"], "Stark")

    def test_adding_user(self):
        r = self.client.get("/api/v3/organizations/", follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)
        root = AccessLevelInstance.objects.get(organization_id=organization_id, depth=1)
        new_user = {
            "organization_id": organization_id,
            "first_name": "Brienne",
            "last_name": "Tarth",
            "email": "test+1@demo.com",
            "role": "member",
            "access_level_instance_id": root.id,
        }

        r = self.client.post(
            "/api/v3/users/?organization_id=" + str(organization_id),
            data=json.dumps(new_user),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(r.status_code, 200)

        r = self.client.get(f"/api/v3/organizations/{organization_id}/", follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r["organization"]["number_of_users"], 2)

        # get org users
        r = self.client.get(f"/api/v3/organizations/{organization_id}/users/", content_type="application/json", **self.headers)
        self.assertEqual(r.status_code, 200)
        # {
        #     "status": "success",
        #     "users": [
        #         {
        #             "role": "owner",
        #             "first_name": "Jaqen",
        #             "last_name": "H'ghar",
        #             "user_id": 1,
        #             "email": "test_user@demo.com"
        #         },
        #         {
        #             "role": "member",
        #             "first_name": "Brienne",
        #             "last_name": "Tarth",
        #             "user_id": 2,
        #             "email": "test+1@demo.com"
        #         }
        #     ]
        # }

        r = json.loads(r.content)
        self.assertEqual(r["status"], "success")
        self.assertEqual(len(r["users"]), 2)

        # get the user id of the new user
        user_id = next(i for i in r["users"] if i["last_name"] == "Tarth")["user_id"]

        # Change the user role
        payload = {"organization_id": organization_id, "role": "owner"}

        r = self.client.put(
            f"/api/v3/users/{user_id}/role/?organization_id={organization_id}",
            data=json.dumps(payload),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r["status"], "success")

        r = self.client.get(f"/api/v3/organizations/{organization_id}/users/", content_type="application/json", **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        new_user = next(i for i in r["users"] if i["last_name"] == "Tarth")
        self.assertEqual(new_user["role"], "owner")

    def test_get_query_threshold(self):
        r = self.client.get("/api/v3/organizations/", follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        r = self.client.get(f"/api/v3/organizations/{organization_id}/query_threshold/", follow=True, **self.headers)
        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["query_threshold"], None)

    def test_shared_fields(self):
        r = self.client.get("/api/v3/organizations/", follow=True, **self.headers)
        r = json.loads(r.content)
        organization_id = self.get_org_id(r, self.user.username)

        r = self.client.get(f"/api/v3/organizations/{organization_id}/shared_fields/", follow=True, **self.headers)

        self.assertEqual(r.status_code, 200)
        r = json.loads(r.content)
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["public_fields"], [])


class TestApiEndpointAuthenticationFailures(TestCase):
    """Invalid credentials on views wrapped by @api_endpoint get a JSON 401 response, not a 500 (#5326).

    The removed APIBypassCSRFMiddleware used to turn these AuthenticationFailed errors into a 401. The version and
    celery_queue views run @api_endpoint outside @api_view, so DRF's exception handling never sees the error.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="test_user@demo.com", password="test_pass", email="test_user@demo.com")
        self.user.generate_key()
        self.superuser = User.objects.create_superuser(
            username="test_superuser@demo.com", password="test_pass", email="test_superuser@demo.com"
        )
        self.superuser.generate_key()

    @staticmethod
    def _basic_auth(username, api_key):
        token = base64.urlsafe_b64encode(f"{username}:{api_key}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def _invalid_credentials(self):
        return [
            ("unknown API key", self._basic_auth(self.user.username, "0" * 40), "Invalid API key or Bearer Token"),
            ("another user's API key", self._basic_auth(self.superuser.username, self.user.api_key), "Invalid API key or Bearer Token"),
            ("malformed API key", self._basic_auth(self.user.username, "not-an-api-key"), "Invalid API key"),
            ("malformed Basic credentials", {"Authorization": "Basic !!!"}, "Invalid HTTP_AUTHORIZATION Header"),
            ("missing Basic credentials", {"Authorization": "Basic"}, "Invalid HTTP_AUTHORIZATION Header"),
            ("blank Basic credentials", {"Authorization": "Basic   "}, "Invalid HTTP_AUTHORIZATION Header"),
            ("invalid Bearer token", {"Authorization": "Bearer not-a-token"}, "Invalid Bearer Token"),
            ("unsupported scheme", {"Authorization": "Token abc"}, "Only Basic HTTP_AUTHORIZATION or BEARER Tokens are supported"),
        ]

    def test_invalid_credentials_return_401(self):
        for url in ("/api/version/", "/api/v3/celery_queue/"):
            for description, headers, message in self._invalid_credentials():
                with self.subTest(url=url, credentials=description):
                    r = self.client.get(url, headers=headers)
                    self.assertEqual(r.status_code, 401)
                    self.assertEqual(r["WWW-Authenticate"], AUTHENTICATE_HEADER)
                    self.assertEqual(r.json(), {"status": "error", "message": message})

    def test_invalid_credentials_return_401_from_seed_org_viewsets(self):
        # SEEDOrg* viewsets list SessionAuthentication first, which has no WWW-Authenticate challenge, so DRF itself
        # would answer invalid credentials with a 403
        org, _, _ = create_organization(self.user)
        for url in (f"/api/v3/cycles/?organization_id={org.id}", f"/api/v3/columns/?organization_id={org.id}"):
            for description, headers, message in self._invalid_credentials():
                with self.subTest(url=url, credentials=description):
                    r = self.client.get(url, headers=headers)
                    self.assertEqual(r.status_code, 401)
                    self.assertEqual(r["WWW-Authenticate"], AUTHENTICATE_HEADER)
                    # The body keeps the view's own error format: {"status": "error", "message": ...} or {"detail": ...}
                    self.assertIn(message, r.json().values())

            with self.subTest(url=url, credentials="valid API key"):
                r = self.client.get(url, headers=self._basic_auth(self.user.username, self.user.api_key))
                self.assertEqual(r.status_code, 200)

            with self.subTest(url=url, credentials="none"):
                # Missing credentials are still rejected as before, with a 403
                r = self.client.get(url)
                self.assertEqual(r.status_code, 403)

    @mock.patch("seed.views.main.subprocess.check_output", return_value=b"abcdef123")
    def test_version_with_valid_api_key(self, check_output):
        r = self.client.get("/api/version/", headers=self._basic_auth(self.user.username, self.user.api_key))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["sha"], "abcdef123")
        check_output.assert_called_once()

    @mock.patch("seed.views.main.app.control.inspect")
    def test_celery_queue_with_valid_api_key(self, inspect):
        # No workers answer, so every task group is reported as "Error"
        for method in ("active", "reserved", "scheduled", "stats"):
            getattr(inspect.return_value, method).return_value = None

        r = self.client.get("/api/v3/celery_queue/", headers=self._basic_auth(self.superuser.username, self.superuser.api_key))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"active": "Error", "reserved": "Error", "scheduled": "Error", "stats": "Error"})

        # A valid key for a user who is not a superuser authenticates, but is not allowed
        r = self.client.get("/api/v3/celery_queue/", headers=self._basic_auth(self.user.username, self.user.api_key))
        self.assertEqual(r.status_code, 403)

    def test_invalid_credentials_return_401_with_a_session(self):
        # A signed-in session must not cause an invalid Authorization header to be ignored. The routes cover the SEEDOrg*
        # authentication classes (cycles), the REST_FRAMEWORK defaults (goals), both without api_endpoint, and a SEEDOrg*
        # action wrapped in api_endpoint (columns).
        org, _, _ = create_organization(self.user)
        self.client.login(username="test_user@demo.com", password="test_pass")
        urls = (
            f"/api/v3/cycles/?organization_id={org.id}",
            f"/api/v3/columns/?organization_id={org.id}",
            f"/api/v3/goals/?organization_id={org.id}",
        )
        for url in urls:
            with self.subTest(url=url, credentials="session only"):
                self.assertEqual(self.client.get(url).status_code, 200)

            with self.subTest(url=url, credentials="session and valid API key"):
                r = self.client.get(url, headers=self._basic_auth(self.user.username, self.user.api_key))
                self.assertEqual(r.status_code, 200)

            for description, headers, message in self._invalid_credentials():
                with self.subTest(url=url, credentials=f"session and {description}"):
                    r = self.client.get(url, headers=headers)
                    self.assertEqual(r.status_code, 401)
                    self.assertEqual(r["WWW-Authenticate"], AUTHENTICATE_HEADER)
                    body = r.json()
                    # With the REST_FRAMEWORK defaults, JWTAuthentication comes first and rejects Bearer tokens itself
                    self.assertTrue(message in body.values() or body.get("code") == "token_not_valid", body)

    def test_deactivated_user_credentials_return_401(self):
        # Deactivating a user only sets is_active=False, so their API key and any unexpired access token must be rejected
        org, _, _ = create_organization(self.user)
        credentials = (
            ("API key", self._basic_auth(self.user.username, self.user.api_key)),
            ("Bearer token", {"Authorization": f"Bearer {AccessToken.for_user(self.user)}"}),
        )
        # SEEDOrg* authentication (cycles), REST_FRAMEWORK defaults (goals), a SEEDOrg* action wrapped in api_endpoint
        # (columns), and the function views that run api_endpoint outside DRF (version, celery_queue)
        inventory_urls = (
            f"/api/v3/cycles/?organization_id={org.id}",
            f"/api/v3/goals/?organization_id={org.id}",
            f"/api/v3/columns/?organization_id={org.id}",
        )
        for url in inventory_urls:
            for description, headers in credentials:
                with self.subTest(url=url, credentials=f"active user's {description}"):
                    self.assertEqual(self.client.get(url, headers=headers).status_code, 200)

        self.user.deactivate_user()

        for url in (*inventory_urls, "/api/version/", "/api/v3/celery_queue/"):
            for description, headers in credentials:
                with self.subTest(url=url, credentials=f"deactivated user's {description}"):
                    r = self.client.get(url, headers=headers)
                    self.assertEqual(r.status_code, 401)
                    self.assertEqual(r["WWW-Authenticate"], AUTHENTICATE_HEADER)
                    self.assertIn("User is inactive", r.json().values())

        # Also with another user's signed-in session
        self.client.login(username="test_superuser@demo.com", password="test_pass")
        for url in inventory_urls:
            with self.subTest(url=url, credentials="session and deactivated user's API key"):
                r = self.client.get(url, headers=credentials[0][1])
                self.assertEqual(r.status_code, 401)
                self.assertIn("User is inactive", r.json().values())

    def test_session_requests_still_need_a_csrf_token(self):
        org, _, _ = create_organization(self.user)
        client = Client(enforce_csrf_checks=True)
        client.login(username="test_user@demo.com", password="test_pass")
        url = f"/api/v3/cycles/?organization_id={org.id}"
        payload = {"name": "CSRF Cycle", "start": "2030-01-01", "end": "2030-12-31"}

        r = client.post(url, data=payload, content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("CSRF", r.content.decode())
        self.assertFalse(Cycle.objects.filter(organization=org, name="CSRF Cycle").exists())

        # A valid API key does not change this: the session authenticates the request, so it still needs a CSRF token
        r = client.post(url, data=payload, content_type="application/json", headers=self._basic_auth(self.user.username, self.user.api_key))
        self.assertEqual(r.status_code, 403)
        self.assertIn("CSRF", r.content.decode())
        self.assertFalse(Cycle.objects.filter(organization=org, name="CSRF Cycle").exists())

        # With the CSRF token the session request succeeds
        csrf_token = "a1" * 16  # an unmasked 32-character CSRF secret
        client.cookies[settings.CSRF_COOKIE_NAME] = csrf_token
        r = client.post(url, data=payload, content_type="application/json", headers={"X-CSRFToken": csrf_token})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(Cycle.objects.filter(organization=org, name="CSRF Cycle").exists())

    def test_drf_views_keep_drf_401_response(self):
        # In a DRF view, api_endpoint leaves the error to DRF, which returns its own 401 response
        org, _, _ = create_organization(self.user)
        self.client.login(username="test_user@demo.com", password="test_pass")
        r = self.client.get(f"/api/v3/organizations/{org.id}/access_levels/tree/", headers=self._basic_auth(self.user.username, "0" * 40))
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json(), {"detail": "Invalid API key or Bearer Token"})
