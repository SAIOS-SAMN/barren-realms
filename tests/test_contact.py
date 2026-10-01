"""
Whether two peoples understand each other follows from what they are and what they have done together; misreading
makes judgement noisy; a shared standard lets peoples understand each other as far as their channel allows.
"""

import random
import unittest

from xylarium.kernel import contact, decide, laws
from xylarium.kernel.engine import GameKernel


class TestContact(unittest.TestCase):
    def test_channels_follow_substrate_temperatures(self):
        biotic = laws.cognition("biotic")["temperature"]
        mineral = laws.cognition("mineral")["temperature"]
        cryo = laws.cognition("cryogenic")["temperature"]
        plasma = laws.cognition("plasmic")["temperature"]
        self.assertAlmostEqual(contact.channel(biotic, biotic), 1.0)
        self.assertGreater(contact.channel(biotic, mineral), contact.channel(cryo, plasma))
        self.assertLess(contact.channel(cryo, plasma), 0.05)

    def test_misreading_makes_judgement_noisy(self):
        m = decide.mind(None, "biotic")
        self.assertAlmostEqual(contact.misread(m, 0.5)["noise"], 2 * m["noise"])

    def test_contact_breeds_familiarity_and_a_standard_brings_understanding(self):
        random.seed(97)
        k = GameKernel(seed=7)
        k.activate()
        by = contact._by(k)
        a, b = list(by)[:2]
        before = contact.intelligibility(k, a, b, by)
        contact.stats(k)["familiarity"][contact._key(a, b)] = 0.9
        self.assertGreaterEqual(contact.intelligibility(k, a, b, by), before)
        contact.stats(k)["protocol"][b] = contact.protocol(k, a)
        shared = contact.intelligibility(k, a, b, by)
        ch = contact.channel(contact._temperature(k, a, by[a]), contact._temperature(k, b, by[b]))
        self.assertAlmostEqual(shared, ch)


if __name__ == "__main__":
    unittest.main()
