"""
Xenon remembers how a world was built: a fast-built embryo closes while iodine-129 lives; a world finished by giant
impacts closes after. Fission xenon cannot raise an air's 129/132 past the solar mix.
"""

import unittest

from xylarium.kernel import noble


class TestNoble(unittest.TestCase):
    def test_mars_closed_before_earth(self):
        self.assertLess(noble.closure_myr(0.107, 1.524), 10.0)          # an embryo: closed in a few Myr
        self.assertGreater(noble.closure_myr(1.0, 1.0), 30.0)           # giant impacts: tens of Myr

    def test_fission_cannot_make_a_xenon_129_excess(self):
        self.assertLess(noble.fission_129_132(), noble.XE_SOLAR[129])


if __name__ == "__main__":
    unittest.main()
