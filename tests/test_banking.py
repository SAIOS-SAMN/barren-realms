"""
Regression tests for federations, central banks, the Galactic Clearing Union (STAMP), the
Galactic ISSE's cross pairs, and the chain-shaped settlement record.
"""

import os
import random
import tempfile
import unittest

from xylarium.config import FX_POOL_SEED, PORT_START_TREASURY, PRICE_LEVEL
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
from xylarium.persistence.store import StatePersistence


def totals(kernel):
    return {c: b["total"] for c, b in money_supply(kernel).items()}


class TestCentralBanks(unittest.TestCase):
    def setUp(self):
        random.seed(31)
        self.kernel = GameKernel(seed=42)
        self.bs = self.kernel.banking

    def test_every_federation_has_a_central_bank_and_sol_is_the_federal_reserve(self):
        self.assertEqual(set(self.bs.banks), {"SOL", "FRN", "THR", "VOID"})
        sol = self.bs.banks["SOL"]
        self.assertEqual(self.bs.reserves(self.kernel, sol), self.kernel.federal_reserve.treasury)
        for cur in ("FRN", "THR", "VOID"):
            self.assertGreater(self.bs.banks[cur].reserves, 0)

    def test_a_bank_buys_back_a_dumped_currency_and_books_it_in_stamp(self):
        pool = self.kernel.fx_market.pools["FRN"]
        pool["local"] = FX_POOL_SEED["FRN"][1] * 2
        rate_before = self.kernel.fx_market.rate("FRN")
        before = totals(self.kernel)
        reserves_before = self.bs.banks["FRN"].reserves
        self.bs._intervene(self.kernel, self.bs.banks["FRN"], self.kernel.settlement)
        self.assertGreater(self.bs.banks["FRN"].reserves, reserves_before)
        self.assertLess(self.kernel.fx_market.rate("FRN"), rate_before)     # the currency firms
        self.assertLess(self.bs.stamp["FRN"], 0)                            # FRN owes the union...
        self.assertAlmostEqual(self.bs.clearing_imbalance(), 0.0, places=6)  # ...and the union nets to zero
        self.assertEqual(before, totals(self.kernel))                       # a transfer, not a mint

    def test_deficit_federations_lend_dearer(self):
        bank = self.bs.banks["FRN"]
        calm = self.bs.rate_for(bank)
        self.bs.stamp["FRN"] = -300_000
        self.bs.stamp["ISSE"] = 300_000
        self.assertGreater(self.bs.rate_for(bank), calm)

    def test_a_dry_port_draws_credit_and_repays_from_later_surplus(self):
        sec = next(s for s in self.kernel.sectors.values() if s.port and s.port.currency == "FRN")
        port = sec.port
        baseline = int(PORT_START_TREASURY * PRICE_LEVEL["FRN"])
        port.treasury = 0
        port.regional_income = baseline * 0.2   # a port whose region reliably pays it: creditworthy
        before = totals(self.kernel)
        bank = self.bs.banks["FRN"]
        self.bs._credit(self.kernel, bank, self.kernel.settlement)
        self.assertGreater(port.treasury, 0)
        self.assertIn(f"port:{sec.id}", bank.loans)
        self.assertEqual(before, totals(self.kernel))
        # A good season: the port's surplus repays the line
        port.treasury = baseline * 3
        debt = bank.loans[f"port:{sec.id}"]["debt"]
        self.bs._credit(self.kernel, bank, self.kernel.settlement)
        self.assertLess(bank.loans.get(f"port:{sec.id}", {"debt": 0})["debt"], debt * 1.05)
        self.assertGreater(bank.stats.get("repaid", 0), 0)

    def test_a_port_with_no_regional_economy_gets_no_credit(self):
        sec = next(s for s in self.kernel.sectors.values() if s.port and s.port.currency == "VOID")
        sec.port.treasury = 0
        sec.port.regional_income = 0.0
        self.bs._credit(self.kernel, self.bs.banks["VOID"], self.kernel.settlement)
        self.assertEqual(sec.port.treasury, 0)
        self.assertNotIn(f"port:{sec.id}", self.bs.banks["VOID"].loans)

    def test_light_governors_cap_interest_and_dark_ones_charge_usury(self):
        bank = self.bs.banks["VOID"]
        bank.alignment = 0.6
        light = self.bs.rate_for(bank)
        bank.alignment = -0.6
        self.assertGreater(self.bs.rate_for(bank), light)


class TestGalacticIsseAndSettlement(unittest.TestCase):
    def setUp(self):
        random.seed(37)
        self.kernel = GameKernel(seed=42)

    def test_cross_pairs_exist_and_best_execution_is_used(self):
        fxm = self.kernel.fx_market
        self.assertIn("FRN/VOID", fxm.cross_pools)
        cap = self.kernel.register_player("fx", "FX Desk")
        cap.fx_wallet["FRN"] = 5000
        before = totals(self.kernel)
        direct = fxm.quote_cross("FRN", "VOID", 5000)
        via = fxm.quote_via_sol("FRN", "VOID", 5000)
        ok, msg, out = fxm.exchange(cap, "FRN", "VOID", 5000)
        self.assertTrue(ok)
        self.assertAlmostEqual(out, max(direct, via), delta=1)   # the SOL hop rounds its intermediate leg
        self.assertIn("Galactic ISSE" if direct > via else "via SOL", msg)
        self.assertEqual(before, totals(self.kernel))

    def test_quarters_seal_a_verifiable_hash_linked_chain(self):
        for _ in range(100):
            self.kernel.tick_simulation()
        chain = self.kernel.settlement
        self.assertEqual(len(chain.blocks), 4)
        self.assertIsNone(chain.verify())
        self.assertEqual(chain.blocks[1]["prev_hash"], chain.blocks[0]["hash"])
        batch = chain.export_batch(since_height=2)
        self.assertEqual(batch["from_height"], 2)
        self.assertEqual(batch["tip"], chain.blocks[-1]["hash"])
        # Tampering with a sealed block breaks verification
        chain.blocks[1]["supply"]["SOL"] += 1
        self.assertIn("block 1", chain.verify())

    def test_banking_and_chain_survive_save_and_load(self):
        for _ in range(50):
            self.kernel.tick_simulation()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "s.json")
            self.assertTrue(StatePersistence.save_to_file(self.kernel, path))
            loaded = StatePersistence.load_from_file(path)
        self.assertEqual(set(loaded.banking.banks), set(self.kernel.banking.banks))
        self.assertEqual(loaded.settlement.blocks[-1]["hash"], self.kernel.settlement.blocks[-1]["hash"])
        self.assertIsNone(loaded.settlement.verify())
        self.assertEqual(set(loaded.fx_market.cross_pools), set(self.kernel.fx_market.cross_pools))


if __name__ == "__main__":
    unittest.main()


class TestPublicWorksAndAnchor(unittest.TestCase):
    def setUp(self):
        random.seed(41)
        self.kernel = GameKernel(seed=42)

    def test_idle_reserves_fund_public_works_without_minting(self):
        bs = self.kernel.banking
        bank = bs.banks["VOID"]
        bank.reserves = 5_000_000
        worlds = [p for s in self.kernel.sectors.values() for p in s.planets if p.population > 0 and p.currency == "VOID"]
        vaults = sum(p.treasury for p in worlds)
        before = totals(self.kernel)
        bs._public_works(self.kernel, bank, money_supply(self.kernel)["VOID"]["total"], self.kernel.settlement)
        self.assertLess(bank.reserves, 5_000_000)
        self.assertGreater(sum(p.treasury for p in worlds), vaults)
        self.assertEqual(before, totals(self.kernel))

    def test_outlaw_houses_are_anchored_in_the_dark_but_players_are_free(self):
        from xylarium.kernel import alignment
        malakor = self.kernel.captains["ai_malakor"]
        malakor.cosmic_alignment = -0.3
        for _ in range(50):
            alignment.deed(self.kernel, malakor, "famine_aid")
        self.assertLessEqual(malakor.cosmic_alignment, -0.2)
        player = self.kernel.register_player("free", "Free Soul", clade="ANARCHY")
        for _ in range(50):
            alignment.deed(self.kernel, player, "famine_aid")
        self.assertGreater(player.cosmic_alignment, 0.0)
