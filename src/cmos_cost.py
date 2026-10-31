"""
CMOS cost of a function of up to 4 inputs (Option 2 handout, section 4, step 4).

A cost is how many static CMOS stages, inverters and transistors it takes to
build the function, with at most 3 transistors in series in any stage.

Construction space (the cheapest valid one is returned):

  1. One complex gate  f = !T(literals), where T is a series-parallel network:
     AND = series NMOS / parallel PMOS, OR = parallel NMOS / series PMOS.
     Literals are inputs or inverted inputs; each inverted input costs one
     inverter (2 transistors) and one extra stage in front.
     Transistors: 2 per literal (one NMOS, one PMOS) plus the inverters.
  2. The same followed by an output inverter: f = !g with g = !T.
  3. Two levels, always possible: a sum of products of f (or of !f followed
     by an inverter) built as AOI gates of at most 3 products of at most 3
     literals each, combined by a NAND of at most 3 inputs (larger sums are
     split into further levels).  A product of 4 literals is split as
     nand2 + inverter feeding a 3-literal product.

  4. Two gates feeding a NAND2 or NOR2:  f = !(g1 & g2) or f = !(g1 | g2),
     each gi a complex gate of construction 1 with at most 5 literals (or a
     plain input), optionally followed by an output inverter.

Constructions 1 and 2 are searched exhaustively up to 8 literals (16
transistors in the gate); construction 4 over all pairs of gates of at most
5 literals.  Construction 3 gives an upper bound for the rest.  Inverters of
the same input used by both gates of construction 4 are counted twice, so its
cost is an upper bound.
"""

import functools
import itertools
from typing import Dict, List, Tuple

VAR_TT = [0xAAAA, 0xCCCC, 0xF0F0, 0xFF00]
NAMES = ['A', 'B', 'C', 'D']
MASK = 0xFFFF
MAX_LITERALS = 8
MAX_SERIES = 3


def _support(tt: int) -> List[int]:
    """Indices of the variables the 16-bit truth table depends on."""
    sup = []
    for v in range(4):
        s = 1 << v
        lo = [i for i in range(16) if not (i & s)]
        if any(((tt >> i) & 1) != ((tt >> (i | s)) & 1) for i in lo):
            sup.append(v)
    return sup


@functools.lru_cache(maxsize=1)
def single_stage_table() -> Dict[int, Tuple[int, int, str]]:
    """
    Exhaustive search over series-parallel networks on the 8 literals
    {A..D, !A..!D}.  Returns {T truth table: (literals, negated-var mask,
    expression of T)} keeping, for each T, the network with the fewest
    literals and, among those, the fewest inverted inputs.  Every network kept
    has at most MAX_SERIES transistors in series in both the NMOS and the PMOS
    network.
    """
    # level[L] : {(tt, n_series, p_series, negmask): expr}
    level: Dict[int, Dict[Tuple[int, int, int, int], str]] = {1: {}}
    for v in range(4):
        level[1][(VAR_TT[v], 1, 1, 0)] = NAMES[v]
        level[1][((~VAR_TT[v]) & MASK, 1, 1, 1 << v)] = f"!{NAMES[v]}"

    best: Dict[int, Tuple[int, int, str]] = {}

    def keep(tt, lits, neg, expr):
        cur = best.get(tt)
        cand = (lits, bin(neg).count('1'))
        if cur is None or cand < (cur[0], bin(cur[1]).count('1')):
            best[tt] = (lits, neg, expr)

    for (tt, n, p, neg), e in level[1].items():
        keep(tt, 1, neg, e)

    for L in range(2, MAX_LITERALS + 1):
        cur: Dict[Tuple[int, int, int, int], str] = {}
        for l1 in range(1, L // 2 + 1):
            l2 = L - l1
            for (t1, n1, p1, g1), e1 in level[l1].items():
                for (t2, n2, p2, g2), e2 in level[l2].items():
                    # AND: NMOS in series, PMOS in parallel
                    n, p = n1 + n2, max(p1, p2)
                    if n <= MAX_SERIES:
                        key = (t1 & t2, n, p, g1 | g2)
                        if key not in cur:
                            cur[key] = f"({e1}&{e2})"
                    # OR: NMOS in parallel, PMOS in series
                    n, p = max(n1, n2), p1 + p2
                    if p <= MAX_SERIES:
                        key = (t1 | t2, n, p, g1 | g2)
                        if key not in cur:
                            cur[key] = f"({e1}|{e2})"
        for (tt, n, p, neg), e in cur.items():
            keep(tt, L, neg, e)
        level[L] = _thin(cur)
    return best


def _thin(nets: Dict[Tuple[int, int, int, int], str]) -> Dict[Tuple[int, int, int, int], str]:
    """
    Keeps, for each (tt, negmask), only the networks not dominated in
    (n_series, p_series): a sub-network with more series transistors and the
    same function and inputs is never better when combined further.
    """
    groups: Dict[Tuple[int, int], List[Tuple[int, int, str]]] = {}
    for (tt, n, p, neg), e in nets.items():
        groups.setdefault((tt, neg), []).append((n, p, e))
    out = {}
    for (tt, neg), lst in groups.items():
        for n, p, e in lst:
            if not any((n2 <= n and p2 <= p and (n2, p2) != (n, p)) for n2, p2, _ in lst):
                out[(tt, n, p, neg)] = e
    return out


def _sop_cubes(tt: int) -> List[Tuple[int, int]]:
    """
    Minimum sum of products of a 4-input function (Quine-McCluskey with an
    exact cover by exhaustive search; at most 16 minterms).
    A cube is (care mask, value): the minterms i with i & care == value.
    """
    minterms = [i for i in range(16) if (tt >> i) & 1]
    if not minterms:
        return []
    cubes = set((0xF, m) for m in minterms)
    primes = set()
    while cubes:
        merged = set()
        used = set()
        for (c1, v1), (c2, v2) in itertools.combinations(cubes, 2):
            if c1 == c2:
                diff = v1 ^ v2
                if bin(diff).count('1') == 1:
                    merged.add((c1 & ~diff, v1 & ~diff))
                    used.add((c1, v1))
                    used.add((c2, v2))
        primes |= cubes - used
        cubes = merged
    primes = sorted(primes, key=lambda c: -bin(0xF & ~c[0]).count('1'))
    cover_of = {c: {m for m in minterms if m & c[0] == c[1]} for c in primes}
    for r in range(1, len(primes) + 1):
        best = None
        for combo in itertools.combinations(primes, r):
            if set().union(*(cover_of[c] for c in combo)) == set(minterms):
                lits = sum(bin(c[0]).count('1') for c in combo)
                if best is None or lits < best[0]:
                    best = (lits, list(combo))
        if best:
            return best[1]
    return primes


def _two_level_cost(tt: int) -> Tuple[int, int, int, str]:
    """
    Construction 3 for f = OR of the cubes of a minimum SOP of f.
    Each AOI gate computes !(up to 3 cubes); a NAND of the AOI outputs (at
    most 3: a minimum SOP of 4 inputs has at most 8 cubes) gives f, or an
    inverter when there is a single AOI.
    Returns (transistors, stages, inverters, expression).
    """
    cubes = _sop_cubes(tt)
    tx, inv, neg_vars, has_split = 0, 0, 0, False
    terms = []
    for care, val in cubes:
        lits = [v for v in range(4) if care >> v & 1]
        for v in lits:
            if not (val >> v & 1):
                neg_vars |= 1 << v
        if len(lits) == 4:
            # 4 literals would put 4 NMOS in series: two of them are first
            # combined by a nand2 and an inverter (6 transistors, 2 stages)
            tx += 6
            inv += 1
            has_split = True
            tx += 2 * 3
        else:
            tx += 2 * len(lits)
        terms.append("&".join(("" if val >> v & 1 else "!") + NAMES[v] for v in lits))
    n_aoi = (len(cubes) + MAX_SERIES - 1) // MAX_SERIES
    if n_aoi == 1:
        tx += 2          # output inverter
        inv += 1
    else:
        tx += 2 * n_aoi  # final NAND
    n_neg = bin(neg_vars).count('1')
    tx += 2 * n_neg
    inv += n_neg
    front = 2 if has_split else (1 if n_neg else 0)
    return tx, front + 2, inv, " | ".join(f"({t})" for t in terms)


@functools.lru_cache(maxsize=1)
def two_gate_table() -> Dict[int, Tuple[int, int, int, str]]:
    """
    Construction 4: {f: (transistors, stages, inverters, expression)} for
    f = !(g1 & g2) and f = !(g1 | g2).
    """
    gates: Dict[int, Tuple[int, int, int, str]] = {}
    for v in range(4):
        gates[VAR_TT[v]] = (0, 0, 0, NAMES[v])
    for t, (lits, neg, e) in single_stage_table().items():
        if lits > 5:
            continue
        n_neg = bin(neg).count('1')
        g = (~t) & MASK
        cand = (2 * lits + 2 * n_neg, 1 + (1 if n_neg else 0), n_neg, f"!{e}")
        if g not in gates or cand[:2] < gates[g][:2]:
            gates[g] = cand
    items = list(gates.items())
    out: Dict[int, Tuple[int, int, int, str]] = {}
    for i, (g1, c1) in enumerate(items):
        for g2, c2 in items[i + 1:]:
            if c1[1] == 0 and c2[1] == 0:
                continue  # a plain nand2/nor2 is construction 1
            base = (c1[0] + c2[0] + 4, max(c1[1], c2[1]) + 1, c1[2] + c2[2])
            for f, op in (((~(g1 & g2)) & MASK, "&"), ((~(g1 | g2)) & MASK, "|")):
                if f not in out or base[:2] < out[f][:2]:
                    out[f] = base + (f"!({c1[3]}{op}{c2[3]})",)
    return out


@functools.lru_cache(maxsize=None)
def cmos_cost(tt: int) -> Dict[str, object]:
    """
    Cost of the function with 16-bit truth table tt (inputs A=bit0 .. D=bit3).
    Returns a dict with stages, inverters, transistors, max_series, construction
    and a Liberty-style expression of the structure.
    """
    tt &= MASK
    if tt in (0, MASK):
        return {"stages": 0, "inverters": 0, "transistors": 0, "max_series": 0,
                "construction": "constant", "expression": "1" if tt else "0"}
    table = single_stage_table()
    cands = []
    # 1. f = !T
    t = (~tt) & MASK
    if t in table:
        lits, neg, e = table[t]
        n_neg = bin(neg).count('1')
        cands.append((2 * lits + 2 * n_neg, 1 + (1 if n_neg else 0), n_neg,
                      "one complex gate", f"!{e}"))
    # 2. f = !(!T): complex gate then output inverter
    if tt in table:
        lits, neg, e = table[tt]
        n_neg = bin(neg).count('1')
        cands.append((2 * lits + 2 * n_neg + 2, 2 + (1 if n_neg else 0), n_neg + 1,
                      "complex gate + output inverter", f"!(!{e})"))
    # 3. two levels, on f and on !f with an output inverter
    tx, st, inv, e = _two_level_cost(tt)
    cands.append((tx, st, inv, "two-level", e))
    tx, st, inv, e = _two_level_cost((~tt) & MASK)
    cands.append((tx + 2, st + 1, inv + 1, "two-level + output inverter", f"!({e})"))

    # 4. two gates into a NAND2/NOR2, without and with an output inverter
    two = two_gate_table()
    if tt in two:
        tx, st, inv, e = two[tt]
        cands.append((tx, st, inv, "two gates + nand2/nor2", e))
    if ((~tt) & MASK) in two:
        tx, st, inv, e = two[(~tt) & MASK]
        cands.append((tx + 2, st + 1, inv + 1, "two gates + nand2/nor2 + output inverter", f"!{e}"))

    tx, st, inv, how, e = min(cands, key=lambda c: (c[0], c[1]))
    return {"stages": st, "inverters": inv, "transistors": tx,
            "max_series": MAX_SERIES, "construction": how, "expression": e}
