"""A captain's turn is one weighed choice: every exclusive action priced, a refused deed struck off and the rest weighed
again, and a trader's goods under contract never counted as its own to sell."""

import random
import unittest
from unittest import mock

from xylarium.kernel import decide, motive, turn
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import AIPersonality


def fresh():
    random.seed(5)
    k = GameKernel(seed=42)
    k.activate()
    return k


def _trader(k):
    return next(c for c in k.captains.values() if c.personality == AIPersonality.TRADER and c.is_ai)


class TestTheTurn(unittest.TestCase):
    def test_a_refused_deed_is_struck_off_and_the_next_is_taken(self):
        k = fresh()
        cap = _trader(k)
        done = []
        refused = mock.Mock(return_value=mock.Mock(success=False))
        opts = [decide.option("refused", 0.0, 100.0, act=refused),
                decide.option("taken", 0.0, 50.0, act=lambda: done.append(1))]
        with mock.patch.object(turn, "options", return_value=opts), \
                mock.patch.object(turn, "side_work"), \
                mock.patch("xylarium.kernel.decide.choose",
                           side_effect=lambda kn, o, m, *a: max(o, key=lambda x: x["value"]) if o else None):
            turn.run(k, cap)
        self.assertTrue(refused.called)
        self.assertEqual(done, [1])

    def test_nothing_worth_it_leaves_the_mind_to_its_books(self):
        k = fresh()
        cap = _trader(k)
        with mock.patch.object(turn, "options", return_value=[]), mock.patch.object(turn, "side_work"), \
                mock.patch("xylarium.kernel.cognition.CognitiveOrgan.think") as think:
            turn.run(k, cap)
        self.assertTrue(think.called)


class TestTraderBooks(unittest.TestCase):
    def test_goods_under_contract_are_not_its_own_to_sell(self):
        k = fresh()
        cap = _trader(k)
        cap.ship.cargo.equipment = 30
        c = mock.Mock(amount=30, commodity="EQUIPMENT")
        k.market_manager.contracts["FRT-T"] = c
        cap.active_contracts = ["FRT-T"]
        self.assertEqual(motive.free_cargo(k, cap, "EQUIPMENT"), 0)
        cap.active_contracts = []
        self.assertEqual(motive.free_cargo(k, cap, "EQUIPMENT"), 30)

    def test_a_lot_carried_on_is_worth_nothing_unheard(self):
        k = fresh()
        cap = _trader(k)
        with mock.patch("xylarium.kernel.comms.known_to", return_value=None):
            self.assertEqual(motive.carried_on(k, cap, cap.sector_id, "ORE", 10), 0.0)


if __name__ == "__main__":
    unittest.main()
