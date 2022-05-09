from django.test import TestCase
from django.urls import reverse


class RobotsTests(TestCase):
    def test_robots(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(200, response.status_code)
