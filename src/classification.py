"""
Boolean Function Classification
Supports P-classes (input permutations), P+N_out classes (permutations + output negation),
and NPN classes (input negations, permutations, output negation).
"""

import functools
import itertools
from typing import Tuple, List, Set, Dict, FrozenSet

# Precompute permutations for 4 variables (S4: 24 permutations)
_S4_PERMS = list(itertools.permutations(range(4)))
_PERM_BIT_MAPS: List[List[int]] = []

for _p in _S4_PERMS:
    # _p maps old input k to new input _p[k]
    # new index idx' has bit _p[k] equal to old bit k
    _idx_map = [0] * 16
    for _idx in range(16):
        _new_idx = sum(((_idx >> _k) & 1) << _p[_k] for _k in range(4))
        _idx_map[_idx] = _new_idx
    _PERM_BIT_MAPS.append(_idx_map)


def permute_tt_16(tt: int, idx_map: List[int]) -> int:
    """Permutes bits of a 16-bit truth table according to idx_map."""
    res = 0
    for old_idx in range(16):
        if (tt >> old_idx) & 1:
            res |= (1 << idx_map[old_idx])
    return res


def depends_on_variable(tt: int, var_idx: int) -> bool:
    """Checks if a 16-bit truth table depends on variable var_idx (0..3)."""
    step = 1 << var_idx
    masks = {
        0: 0x5555,
        1: 0x3333,
        2: 0x0F0F,
        3: 0x00FF
    }
    return bool(((tt >> step) ^ tt) & masks[var_idx])


def active_variables(tt: int) -> Tuple[int, ...]:
    """Returns sorted tuple of variable indices (0..3) that tt actually depends on."""
    return tuple(i for i in range(4) if depends_on_variable(tt, i))


def depends_on_all_4(tt: int) -> bool:
    """Checks if a 16-bit truth table is non-degenerate (depends on all 4 inputs)."""
    return (depends_on_variable(tt, 0) and
            depends_on_variable(tt, 1) and
            depends_on_variable(tt, 2) and
            depends_on_variable(tt, 3))


@functools.lru_cache(maxsize=65536)
def _cached_p_orbit(tt: int) -> Tuple[int, FrozenSet[int]]:
    tt &= 0xFFFF
    min_tt = tt
    all_tts: Set[int] = set()
    for idx_map in _PERM_BIT_MAPS:
        ptt = permute_tt_16(tt, idx_map)
        all_tts.add(ptt)
        if ptt < min_tt:
            min_tt = ptt
    return min_tt, frozenset(all_tts)


def get_p_class(tt: int) -> Tuple[int, Set[int]]:
    """
    Returns (canonical_p_rep, all_permuted_tts) under S4 input permutations.
    Canonical representative is the minimum 16-bit integer in the orbit.
    """
    min_tt, orbit = _cached_p_orbit(tt & 0xFFFF)
    return min_tt, set(orbit)


@functools.lru_cache(maxsize=65536)
def get_p_nout_class(tt: int) -> int:
    """
    Returns canonical representative under input permutation and output inversion (Step 3).
    """
    tt &= 0xFFFF
    rep_pos, _ = _cached_p_orbit(tt)
    rep_neg, _ = _cached_p_orbit((~tt) & 0xFFFF)
    return min(rep_pos, rep_neg)


@functools.lru_cache(maxsize=65536)
def get_npn_class(tt: int) -> int:
    """
    Returns canonical representative under full NPN equivalence
    (16 input polarity combinations x 24 input permutations x 2 output polarities = 768 transformations).
    """
    tt &= 0xFFFF
    min_tt = tt
    for neg_mask in range(16):
        # Apply input negations: if bit k of neg_mask is 1, negate input k
        neg_tt = 0
        for idx in range(16):
            if (tt >> idx) & 1:
                neg_tt |= (1 << (idx ^ neg_mask))

        rep_pos, _ = _cached_p_orbit(neg_tt)
        if rep_pos < min_tt:
            min_tt = rep_pos
        rep_neg, _ = _cached_p_orbit((~neg_tt) & 0xFFFF)
        if rep_neg < min_tt:
            min_tt = rep_neg

    return min_tt
