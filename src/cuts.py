#!/usr/bin/env python3
"""Option 2, step 2: k-feasible cut enumeration (k<=4) with a truth table per cut.

Reads ASCII (aag) or binary (aig) AIGER. Run it on a STRASHED file (ABC's `strash`), or duplicate
nodes inflate the cut counts.

Conventions
  * AIGER literal = 2*var + negation; var 0 is constant 0.
  * Latch outputs are treated as primary inputs (cut leaves).
  * A cut is (leaves, tt): leaves = sorted tuple of var ids; tt has 2**len(leaves) bits;
    bit m of tt is the root value when leaf i equals bit i of m (leaf 0 = least significant input).
  * Cuts whose leaves lie inside each other's cones are dropped: their truth table would depend on
    leaf combinations that cannot occur, so it would not be a function of the leaves.
Usage: cuts.py file.aag|file.aig [--k 4] [--check]
"""
import sys, argparse
from functools import lru_cache

class Aig:
    def __init__(self, inputs, latches, outputs, ands):
        self.inputs, self.latches, self.outputs, self.ands = inputs, latches, outputs, ands
        self.leaf_vars = set(inputs) | set(latches)

def load(path):
    with open(path, "rb") as f:
        data = f.read()
    head, _, rest = data.partition(b"\n")
    h = head.split()
    kind = h[0].decode()
    M, I, L, O, A = map(int, h[1:6])
    if kind == "aag":
        lines = rest.decode().split("\n")
        p = 0
        inputs = [int(lines[p + i]) // 2 for i in range(I)]; p += I
        latches = [int(lines[p + i].split()[0]) // 2 for i in range(L)]; p += L
        outputs = [int(lines[p + i]) for i in range(O)]; p += O
        ands = {}
        for i in range(A):
            l, a, b = map(int, lines[p + i].split())
            ands[l // 2] = (a, b)
        return Aig(inputs, latches, outputs, ands)
    assert kind == "aig", "not an AIGER file"
    inputs = list(range(1, I + 1))
    latches = list(range(I + 1, I + L + 1))
    pos = 0
    for _ in range(L + O):                      # latch next-state lines and outputs: ASCII
        pos = rest.index(b"\n", pos) + 1
    outputs = []                                # (not needed by cut enumeration)
    def delta():
        nonlocal pos
        x, shift = 0, 0
        while True:
            c = rest[pos]; pos += 1
            x |= (c & 0x7F) << shift
            if not (c & 0x80): return x
            shift += 7
    ands = {}
    for i in range(A):
        lhs = 2 * (I + L + 1 + i)
        r0 = lhs - delta()
        r1 = r0 - delta()
        ands[lhs // 2] = (r0, r1)
    return Aig(inputs, latches, outputs, ands)

@lru_cache(maxsize=None)
def _expand(tt, leaves, merged):
    """Re-express tt (a table over `leaves`) as a table over the superset `merged`."""
    pos = [merged.index(x) for x in leaves]
    out = 0
    for m in range(1 << len(merged)):
        idx = 0
        for i, p in enumerate(pos):
            idx |= ((m >> p) & 1) << i
        if (tt >> idx) & 1:
            out |= 1 << m
    return out

def enumerate_cuts(g, k=4):
    """Return {var: [(leaves, tt, cone), ...]}; cone = frozenset of internal nodes (excludes leaves).
    The last entry of each AND node's list is its trivial cut."""
    cuts = {0: [((), 0, frozenset())]}
    for v in g.leaf_vars:
        cuts[v] = [((v,), 0b10, frozenset())]
    dropped = 0
    for v in sorted(g.ands):
        a, b = g.ands[v]
        res = {}
        for la, ta, ca in cuts[a >> 1]:
            for lb, tb, cb in cuts[b >> 1]:
                merged = tuple(sorted(set(la) | set(lb)))
                if len(merged) > k:
                    continue
                if not set(la).isdisjoint(cb) or not set(lb).isdisjoint(ca):
                    dropped += 1
                    continue
                full = (1 << (1 << len(merged))) - 1
                xa = _expand(ta, la, merged) if la else 0
                xb = _expand(tb, lb, merged) if lb else 0
                if a & 1: xa ^= full
                if b & 1: xb ^= full
                if merged not in res:
                    res[merged] = (xa & xb, ca | cb | {v})
        cuts[v] = [(l, t, c) for l, (t, c) in sorted(res.items())] + [((v,), 0b10, frozenset())]
    g.dropped = dropped
    return cuts

def simulate(g, v, val):
    """Evaluate node v with leaf values in `val` (a dict var -> 0/1), descending through ANDs."""
    if v in val: return val[v]
    if v == 0: return 0
    a, b = g.ands[v]
    r = (simulate(g, a >> 1, val) ^ (a & 1)) & (simulate(g, b >> 1, val) ^ (b & 1))
    val[v] = r
    return r

def check_cuts(g, cuts):
    """Independent check: for every cut and every leaf assignment, simulate the AIG down to the
    leaves and compare with the stored truth table. Returns a list of failures."""
    bad = []
    for v, lst in cuts.items():
        if v not in g.ands: continue
        for leaves, tt, _ in lst:
            if leaves == (v,): continue
            for m in range(1 << len(leaves)):
                val = {leaves[i]: (m >> i) & 1 for i in range(len(leaves))}
                if simulate(g, v, val) != ((tt >> m) & 1):
                    bad.append((v, leaves, m)); break
    return bad

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("aig"); ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    g = load(a.aig)
    c = enumerate_cuts(g, a.k)
    n = sum(len(l) - 1 for v, l in c.items() if v in g.ands)
    print(f"ands={len(g.ands)} cuts={n} dropped_overlapping={g.dropped}")
    if a.check:
        bad = check_cuts(g, c)
        print("CHECK", "FAIL" if bad else "PASS", len(bad))
        sys.exit(1 if bad else 0)
