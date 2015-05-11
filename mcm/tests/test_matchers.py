from unittest import TestCase

from mcm import matchers


class TestMatchers(TestCase):

    def test_case_insensitivity(self):
        """Make sure we disregard case when doing comparisons."""
        fake_comp = 'TeST'
        fake_categories = ['test', 'thing', 'face']
        match, percent = matchers.best_match(
            fake_comp, fake_categories, top_n=1
        )[0]

        self.assertEqual(match, 'test')
        self.assertEqual(percent, 100)
