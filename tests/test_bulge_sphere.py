"""
The bulge is a sphere: a star near the galaxy's axis but far above its plane is not in the core.
"""

import unittest
from unittest import mock

from xylarium.kernel import cosmos, creation, geometry
from xylarium.kernel.engine import GameKernel


class TestBulgeSphere(unittest.TestCase):
    def test_a_mind_far_above_the_plane_is_not_born_in_the_core(self):
        k = GameKernel(seed=42)
        mind = {"cell": [0, 0], "k": 0, "epoch": 1.0}
        self.assertTrue(cosmos.in_core(mind))                                 # on the plane, near the axis
        with mock.patch.object(creation, "cell", return_value=[{"vertical": {"x": 1}}]), \
                mock.patch.object(geometry, "z_at", return_value=cosmos.R_BULGE_KPC * 2):
            self.assertFalse(cosmos.in_core(mind, k))                         # far above it: outside the sphere


if __name__ == "__main__":
    unittest.main()
