from django.urls import reverse
from django.test import TestCase


class RobotsTests(TestCase):
    def test_robots(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(200, response.status_code)
