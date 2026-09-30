"""
Architecture tests (docs/STANDARDS.md, S7): the standards that can be checked mechanically are checked here, so a
change that re-introduces a hand-rolled search, lazy kernel state, a write into configuration, an unregistered
seasonal hook or an unbounded engine fails the suite.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KERNEL = os.path.join(ROOT, "xylarium", "kernel")
ENGINE_LINE_BUDGET = 2800


def kernel_sources():
    for name in sorted(os.listdir(KERNEL)):
        if name.endswith(".py"):
            path = os.path.join(KERNEL, name)
            with open(path, encoding="utf-8") as f:
                yield name, f.read()


class TestArchitecture(unittest.TestCase):
    def test_S3_graph_searches_live_in_topology(self):
        """No breadth-first search over warps outside topology.py (fibres' weighted geodesics are its own)."""
        offenders = []
        for name, src in kernel_sources():
            if name in ("topology.py", "fibres.py"):
                continue
            lines = src.splitlines()
            for i, line in enumerate(lines):
                if re.search(r"for \w+ in .*\.warps\b", line):
                    window = "\n".join(lines[i:i + 4])
                    if re.search(r"\b(dist|seen|visited|frontier)\b", window):
                        offenders.append(f"{name}:{i + 1}")
        self.assertEqual(offenders, [], "breadth-first searches belong in topology.py")

    def test_S2_no_lazy_kernel_state(self):
        """Subsystem state lives in kernel.state (state.of), not in attributes attached to the kernel on first use."""
        offenders = []
        for name, src in kernel_sources():
            if name in ("state.py", "cache.py", "topology.py"):
                continue
            for m in re.finditer(r'getattr\((kernel|self|k), "([a-z_]+)", None\)', src):
                who, attr = m.group(1), m.group(2)
                tail = src[m.end():m.end() + 400]
                if re.search(rf"\b{who}\.{attr}\s*=", tail):
                    offenders.append(f"{name}: {who}.{attr}")
            for m in re.finditer(r"\b(kernel|k)\.(_[a-z_]+)\s*=(?!=)", src):
                offenders.append(f"{name}: {m.group(1)}.{m.group(2)}")
        self.assertEqual(offenders, [], "use state.of(kernel, name) and cache.memo")

    def test_S5_configuration_is_never_written(self):
        offenders = []
        for name, src in kernel_sources():
            for m in re.finditer(r"\b(SHIP_CATALOG|COMMODITY_CONFIG|SHIP_FRAMES|SHIP_MODULES|FUEL_CELLS)"
                                 r"(\[[^\]]+\]\s*=(?!=)|\.update\(|\.setdefault\(|\.pop\()", src):
                offenders.append(f"{name}: {m.group(0)}")
        self.assertEqual(offenders, [], "configuration is read-only; runtime records live on the kernel")

    def test_S1_the_engine_runs_the_season_through_the_registry(self):
        with open(os.path.join(KERNEL, "engine.py"), encoding="utf-8") as f:
            engine = f.read()
        self.assertIsNone(re.search(r"\w+_mod\.(quarter|season)\(self\)", engine),
                          "seasonal hooks are registered subsystems, run by subsystem.run_season")
        import xylarium.kernel.engine  # noqa: F401  (registers every subsystem)
        from xylarium.kernel import subsystem
        for name in subsystem.SEASON:
            sub = subsystem.get(name)
            self.assertIsNotNone(sub, f"{name} is in the season but not registered")
            self.assertIsNotNone(sub.season, f"{name} is in the season but has no seasonal hook")

    def test_S6_commands_are_registered_not_branched(self):
        with open(os.path.join(KERNEL, "engine.py"), encoding="utf-8") as f:
            engine = f.read()
        self.assertLessEqual(len(re.findall(r"elif action == ActionType\.", engine)), 2)
        from xylarium.kernel import actions
        from xylarium.kernel.models import ActionType
        self.assertIn(ActionType.MOVE, actions.REGISTRY)
        self.assertGreater(len(actions.REGISTRY), 90)

    def test_engine_line_budget(self):
        with open(os.path.join(KERNEL, "engine.py"), encoding="utf-8") as f:
            n = sum(1 for _ in f)
        self.assertLessEqual(n, ENGINE_LINE_BUDGET, "engine.py grows only by delegation, not by new systems")


if __name__ == "__main__":
    unittest.main()
