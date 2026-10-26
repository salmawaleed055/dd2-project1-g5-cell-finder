#!/usr/bin/env python3
"""Cut enumerator check, and its broken case. Run: python3 tests/test_cuts.py"""
import os, random, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import cuts

def random_aag(path, inputs=8, ands=200, seed=1):
    random.seed(seed)
    lits = [2 * i for i in range(1, inputs + 1)]
    rows, nxt = [], inputs + 1
    for _ in range(ands):
        a = random.choice(lits) ^ random.randint(0, 1)
        b = random.choice(lits) ^ random.randint(0, 1)
        while (a >> 1) == (b >> 1):
            b = random.choice(lits) ^ random.randint(0, 1)
        rows.append((2 * nxt, a, b)); lits.append(2 * nxt); nxt += 1
    with open(path, "w") as f:
        f.write(f"aag {inputs + ands} {inputs} 0 1 {ands}\n")
        for i in range(1, inputs + 1): f.write(f"{2 * i}\n")
        f.write(f"{rows[-1][0]}\n")
        for r in rows: f.write(f"{r[0]} {r[1]} {r[2]}\n")

def main():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.aag"); random_aag(p)
        g = cuts.load(p); c = cuts.enumerate_cuts(g, 4)
        # 1. the check must pass on correct cuts
        assert cuts.check_cuts(g, c) == [], "check failed on a correct enumeration"
        print("PASS: all cuts agree with simulation")
        # 2. broken case: flip one bit of one truth table; the check must catch it
        v = next(v for v in sorted(g.ands) if len(c[v]) > 2)
        leaves, tt, cone = c[v][0]
        c[v][0] = (leaves, tt ^ 1, cone)
        bad = cuts.check_cuts(g, c)
        assert bad and bad[0][0] == v, "BROKEN CASE NOT CAUGHT"
        print(f"PASS: broken truth table at node {v} was caught")

if __name__ == "__main__":
    main()
