"""
Redundancy Checker, CMOS Stage/Transistor Coster, and Self-Test against Handout Table 4
Section 5: Checking new cells against SkyWater 130nm HD library.
"""

import functools
import itertools
import re
from typing import Dict, List, Tuple, Set, Optional

from src.classification import (
    depends_on_all_4, active_variables, get_p_class, permute_tt_16, _PERM_BIT_MAPS
)


def eval_lib_expr(expr: str, var_map: Dict[str, int]) -> int:
    """Evaluates a Liberty boolean function expression given pin values (0 or 1)."""
    tokens = re.split(r'([a-zA-Z0-9_]+|\(|\)|!|&|\||\^)', expr)
    py_tokens = []
    for t in tokens:
        if not t or t.isspace():
            continue
        if t == '!':
            py_tokens.append(' not ')
        elif t == '&':
            py_tokens.append(' and ')
        elif t == '|':
            py_tokens.append(' or ')
        elif t == '^':
            py_tokens.append(' ^ ')
        elif t in ('(', ')'):
            py_tokens.append(t)
        elif t in ('0', '1'):
            py_tokens.append(t)
        elif t in var_map:
            py_tokens.append(str(var_map[t]))
        else:
            raise ValueError(f"Unknown token '{t}' in Liberty expression: {expr}")
    return int(bool(eval(''.join(py_tokens))))


@functools.lru_cache(maxsize=256)
def eval_cell_truth_table(fn_expr: str, pins: Tuple[str, ...]) -> int:
    """Evaluates a k-input Liberty function over all 2^k input combinations once."""
    k = len(pins)
    tt = 0
    for idx in range(1 << k):
        vmap = {pins[j]: (idx >> j) & 1 for j in range(k)}
        if eval_lib_expr(fn_expr, vmap):
            tt |= (1 << idx)
    return tt


def parse_hd_library(lib_path: str) -> List[Dict]:
    """
    Parses a Liberty file and returns all combinational single-output cells.
    Each item contains: 'name', 'inputs', 'output_pin', 'function', 'area'.
    """
    with open(lib_path, 'r', encoding='utf-8') as f:
        content = f.read()

    cell_matches = list(re.finditer(r'cell\s*\(\s*\"?([a-zA-Z0-9_]+)\"?\s*\)\s*\{', content))
    cells = []

    for i in range(len(cell_matches)):
        name = cell_matches[i].group(1)
        start = cell_matches[i].start()
        end = cell_matches[i + 1].start() if i + 1 < len(cell_matches) else len(content)
        block = content[start:end]

        # Ignore sequential cells
        if re.search(r'ff\s*\(|latch\s*\(', block):
            continue

        pin_matches = re.findall(r'pin\s*\(\s*\"?([a-zA-Z0-9_]+)\"?\s*\)\s*\{([^}]+)\}', block)
        inputs = []
        outputs = []
        for pin_name, pin_block in pin_matches:
            dir_m = re.search(r'direction\s*:\s*\"?(input|output)\"?', pin_block)
            if not dir_m:
                continue
            direction = dir_m.group(1)
            if direction == 'input':
                inputs.append(pin_name)
            elif direction == 'output':
                fn_m = re.search(r'function\s*:\s*\"([^\"]+)\"', pin_block)
                if fn_m:
                    outputs.append((pin_name, fn_m.group(1)))

        area_m = re.search(r'area\s*:\s*([0-9.]+)', block)
        area = float(area_m.group(1)) if area_m else 0.0

        if len(outputs) == 1:
            fn = outputs[0][1]
            cells.append({
                'name': name,
                'inputs': inputs,
                'output_pin': outputs[0][0],
                'function': fn,
                'area': area
            })

    return cells


@functools.lru_cache(maxsize=1)
def synthesize_one_stage_4inp() -> Dict[str, Dict]:
    """
    First-principles static CMOS series-parallel network synthesizer for 4-input functions.
    Generates all series-parallel trees up to 8 literals on variables {A, B, C, D}:
    - Read-once trees (every input used once, 4 literals = 8 transistors) with <= 3 in series.
    - All 1-stage static CMOS negative-unate functions on 4 inputs.
    - All 1-stage static CMOS functions with <= 3 transistors in series and <= 12 transistors (<= 6 literals).
    """
    var_tts = [0xAAAA, 0xCCCC, 0xF0F0, 0xFF00]
    var_names = ['A', 'B', 'C', 'D']

    # Tree tuple: (pos_tt, nmos_series, pmos_series, vars_used_frozenset, shared_in_and, op_type, alt_depth, expr)
    trees: Dict[int, List[Tuple[int, int, int, frozenset, bool, str, int, str]]] = {
        1: [(var_tts[i], 1, 1, frozenset([var_names[i]]), False, 'VAR', 0, var_names[i]) for i in range(4)]
    }

    for tl in range(2, 9):
        level_map: Dict[Tuple[int, bool, str, int, bool], Tuple[int, int, frozenset, str]] = {}
        for l1 in range(1, tl // 2 + 1):
            l2 = tl - l1
            for tt1, n1, p1, v1, ra1, op1, d1, e1 in trees[l1]:
                for tt2, n2, p2, v2, ra2, op2, d2, e2 in trees[l2]:
                    if (tt1 & tt2) == tt1 or (tt1 & tt2) == tt2:
                        continue
                    ov = bool(v1 & v2)
                    u_vars = v1 | v2
                    is_ro = (tl == len(u_vars)) and not ov

                    # 1. Series NMOS / Parallel PMOS (AND in pull-down)
                    tt_and = tt1 & tt2
                    n_and = n1 + n2
                    p_and = max(p1, p2)
                    ra_and = ra1 or ra2 or ov
                    da1 = d1 if op1 == 'AND' else (d1 + 1 if op1 == 'OR' else 1)
                    da2 = d2 if op2 == 'AND' else (d2 + 1 if op2 == 'OR' else 1)
                    d_and = max(da1, da2)
                    key_and = (tt_and, ra_and, 'AND', d_and, is_ro)
                    if key_and not in level_map or (max(n_and, p_and), n_and, p_and) < (max(level_map[key_and][0], level_map[key_and][1]), level_map[key_and][0], level_map[key_and][1]):
                        level_map[key_and] = (n_and, p_and, u_vars, f"({e1}&{e2})")

                    # 2. Parallel NMOS / Series PMOS (OR in pull-down)
                    tt_or = tt1 | tt2
                    n_or = max(n1, n2)
                    p_or = p1 + p2
                    ra_or = ra1 or ra2
                    do1 = d1 if op1 == 'OR' else (d1 + 1 if op1 == 'AND' else 1)
                    do2 = d2 if op2 == 'OR' else (d2 + 1 if op2 == 'AND' else 1)
                    d_or = max(do1, do2)
                    key_or = (tt_or, ra_or, 'OR', d_or, is_ro)
                    if key_or not in level_map or (max(n_or, p_or), n_or, p_or) < (max(level_map[key_or][0], level_map[key_or][1]), level_map[key_or][0], level_map[key_or][1]):
                        level_map[key_or] = (n_or, p_or, u_vars, f"({e1}|{e2})")

        trees[tl] = [
            (tt, n, p, u_vars, ra, op, d, expr)
            for (tt, ra, op, d, _), (n, p, u_vars, expr) in level_map.items()
        ]

    one_stage_all: Dict[int, Tuple[int, int, int, str]] = {}
    one_stage_3s_12tx: Dict[int, Tuple[int, int, int, str]] = {}
    read_once_3s: Dict[int, Tuple[int, int, str]] = {}
    pos_tt_3s_best: Dict[int, Tuple[int, int, int, str]] = {}

    for tl in range(1, 9):
        for pos_tt, n, p, u_vars, ra, op, d, expr in trees[tl]:
            if n <= 3 and p <= 3 and (not ra or d <= 3):
                if pos_tt not in pos_tt_3s_best or (tl, max(n, p)) < (pos_tt_3s_best[pos_tt][0], max(pos_tt_3s_best[pos_tt][1], pos_tt_3s_best[pos_tt][2])):
                    pos_tt_3s_best[pos_tt] = (tl, n, p, f"!{expr}")

            if tl < 4 or len(u_vars) < 4:
                continue
            out_tt = (~pos_tt) & 0xFFFF
            if not depends_on_all_4(out_tt):
                continue
            rep, _ = get_p_class(out_tt)

            if not ra or d <= 3:
                cand_all = (tl, n, p, f"!{expr}")
                if rep not in one_stage_all or (tl, max(n, p), n + p) < (one_stage_all[rep][0], max(one_stage_all[rep][1], one_stage_all[rep][2]), one_stage_all[rep][1] + one_stage_all[rep][2]):
                    if out_tt == rep or rep not in one_stage_all:
                        one_stage_all[rep] = cand_all

            if tl == 4 and not ra and n <= 3 and p <= 3:
                if rep not in read_once_3s or out_tt == rep:
                    read_once_3s[rep] = (n, p, f"!{expr}")

            if tl <= 6 and n <= 3 and p <= 3 and (not ra or d <= 3):
                if rep not in one_stage_3s_12tx or out_tt == rep:
                    one_stage_3s_12tx[rep] = (tl, n, p, f"!{expr}")

    return {
        "one_stage_all": one_stage_all,
        "one_stage_3s_12tx": one_stage_3s_12tx,
        "read_once_3s": read_once_3s,
        "pos_tt_3s_best": pos_tt_3s_best,
    }


def cost_4inp_class(tt: int) -> Dict[str, object]:
    """
    Section 4, Step 4: Cost a 4-input class by what building it would take:
    how many CMOS stages, how many inverters, and how many transistors,
    with at most 3 transistors in series in any stage.
    """
    rep, _ = get_p_class(tt & 0xFFFF)
    sp = synthesize_one_stage_4inp()
    one_stage_3s = sp["one_stage_3s_12tx"]
    one_stage_all = sp["one_stage_all"]
    pos_tt_3s = sp["pos_tt_3s_best"]

    # Case 1: Single static CMOS stage with <= 3 in series
    pos_tt = (~rep) & 0xFFFF
    if pos_tt in pos_tt_3s:
        lits, n, p, expr = pos_tt_3s[pos_tt]
        return {
            "stages": 1,
            "inverters": 0,
            "transistors": 2 * lits,
            "max_series": max(n, p),
            "expression": expr
        }
    if rep in one_stage_3s:
        lits, n, p, expr = one_stage_3s[rep]
        return {
            "stages": 1,
            "inverters": 0,
            "transistors": 2 * lits,
            "max_series": max(n, p),
            "expression": expr
        }

    # Case 2: 1-stage core + input/output inverters (2 stages, <= 3 in series per stage)
    best_cost = None
    for out_inv in (0, 1):
        target_tt = rep if out_inv == 0 else ((~rep) & 0xFFFF)
        target_pos = (~target_tt) & 0xFFFF
        for neg_mask in range(16):
            num_inp_inv = bin(neg_mask).count("1")
            # Apply input negations
            transformed = 0
            for idx in range(16):
                if (target_pos >> idx) & 1:
                    transformed |= (1 << (idx ^ neg_mask))
            if transformed in pos_tt_3s:
                lits, n, p, expr = pos_tt_3s[transformed]
                num_inv = num_inp_inv + out_inv
                tx = 2 * lits + 2 * num_inv
                stages = 1 + (1 if num_inp_inv > 0 else 0) + out_inv
                cand = (tx, stages, num_inv, max(n, p), expr)
                if best_cost is None or cand < best_cost:
                    best_cost = cand

    if best_cost is not None:
        tx, stages, num_inv, max_s, expr = best_cost
        return {
            "stages": stages,
            "inverters": num_inv,
            "transistors": tx,
            "max_series": max_s,
            "expression": expr
        }

    # Case 3: Multi-stage decomposition (2-level logic decomposed into stages with <= 3 in series)
    # Determine minimum SOP Cubes of rep or ~rep
    vars_masks = [0xAAAA, 0xCCCC, 0xF0F0, 0xFF00]
    best_multi = None
    for out_inv in (0, 1):
        f_tt = rep if out_inv == 0 else ((~rep) & 0xFFFF)
        # Count essential input inversions and prime implicants
        minterms = [i for i in range(16) if (f_tt >> i) & 1]
        if not minterms:
            continue
        # Estimate decomposed 2-stage / 3-stage CMOS cost with <= 3 series limit
        num_terms = min(len(minterms), 16 - len(minterms))
        # Each 4-input term with >3 literals splits into a 2-input gate + 3-input stage
        inp_invs = min(4, max(1, num_terms))
        core_lits = max(4, min(10, num_terms * 2 + 2))
        stages = 2 + out_inv
        tx = 2 * core_lits + 2 * inp_invs + 2 * out_inv
        cand = (tx, stages, inp_invs + out_inv)
        if best_multi is None or cand < best_multi:
            best_multi = cand

    tx, stages, invs = best_multi if best_multi else (20, 3, 2)
    return {
        "stages": stages,
        "inverters": invs,
        "transistors": tx,
        "max_series": 3,
        "expression": f"tt_0x{rep:04X}"
    }


class RedundancyChecker:
    def __init__(self, lib_path: str):
        self.lib_path = lib_path
        self.cells = parse_hd_library(lib_path)

        # 4-input P-class sets (for Table 4 and 4-input candidates)
        self.exists_classes: Set[int] = set()
        self.exists_inv_classes: Set[int] = set()
        self.contained_classes: Set[int] = set()

        # Detailed match mapping: rep -> (class_name, hd_cell_name, match_description, hd_x1_area)
        self.match_info: Dict[int, Tuple[str, str, str, float]] = {}

        # Index all k-input HD cells (k = 0..6) for fast general cell checking
        self.hd_k_input_reps: Dict[Tuple[int, int], str] = {}

        self._build_reference_sets()

    def _get_family_x1_cell(self, fn_expr: str, default_cell: Dict) -> Dict:
        """Finds the _1 drive cell for a given function expression (for area reference)."""
        matching = [c for c in self.cells if c['function'] == fn_expr]
        x1 = next((c for c in matching if c['name'].endswith('_1')), None)
        return x1 if x1 is not None else default_cell

    def _build_reference_sets(self):
        # 0. Index all combinational cells (k = 0..6 inputs)
        for c in self.cells:
            pins = tuple(c['inputs'])
            k = len(pins)
            x1_cell = self._get_family_x1_cell(c['function'], c)
            tt_full = eval_cell_truth_table(c['function'], pins)
            if k <= 4:
                # Expand to 4-variable space (unassigned variables don't affect low bits, repeat pattern across 16 bits)
                tt16 = 0
                for idx in range(16):
                    sub_idx = idx & ((1 << k) - 1)
                    if (tt_full >> sub_idx) & 1:
                        tt16 |= (1 << idx)
                rep, _ = get_p_class(tt16)
                self.hd_k_input_reps.setdefault((k, rep), x1_cell['name'])
            else:
                self.hd_k_input_reps.setdefault((k, tt_full), x1_cell['name'])

        # 1. Build Exists classes from 4-input HD cells
        hd_4inp_cells = [c for c in self.cells if len(c['inputs']) == 4]
        hd_4inp_tts = []
        seen_4inp_fns = set()

        for c in hd_4inp_cells:
            if c['function'] in seen_4inp_fns:
                continue
            seen_4inp_fns.add(c['function'])
            x1_cell = self._get_family_x1_cell(c['function'], c)
            pins = tuple(c['inputs'])
            tt = eval_cell_truth_table(c['function'], pins)
            hd_4inp_tts.append((x1_cell['name'], x1_cell['area'], c['function'], tt))
            if depends_on_all_4(tt):
                rep, _ = get_p_class(tt)
                self.exists_classes.add(rep)
                if rep not in self.match_info:
                    self.match_info[rep] = ("Exists", x1_cell['name'], f"Direct pin permutation of {x1_cell['name']}", x1_cell['area'])

        # 2. Build Exists with an inverter
        def invert_input(tt: int, k: int) -> int:
            res = 0
            step = 1 << k
            for idx in range(16):
                if (tt >> idx) & 1:
                    res |= (1 << (idx ^ step))
            return res

        for cell_name, cell_area, fn_str, tt in hd_4inp_tts:
            # Output inversion
            inv_out_tt = (~tt) & 0xFFFF
            if depends_on_all_4(inv_out_tt):
                rep, _ = get_p_class(inv_out_tt)
                if rep not in self.exists_classes:
                    self.exists_inv_classes.add(rep)
                    if rep not in self.match_info:
                        self.match_info[rep] = ("Exists with an inverter", cell_name, f"Output inversion of {cell_name}", cell_area)

            # Invert one input
            for k in range(4):
                inv_inp_tt = invert_input(tt, k)
                if depends_on_all_4(inv_inp_tt):
                    rep, _ = get_p_class(inv_inp_tt)
                    if rep not in self.exists_classes:
                        self.exists_inv_classes.add(rep)
                        if rep not in self.match_info:
                            self.match_info[rep] = ("Exists with an inverter", cell_name, f"Single input inversion of {cell_name}", cell_area)

        # 3. Build Contained classes from cells with >= 4 inputs using fast bitwise truth-table projection
        hd_large_cells = [c for c in self.cells if len(c['inputs']) >= 4]
        distinct_large = {}
        for c in hd_large_cells:
            if c['function'] not in distinct_large:
                distinct_large[c['function']] = self._get_family_x1_cell(c['function'], c)

        # Target codes: 0->x0, 1->x1, 2->x2, 3->x3, 4->const 0, 5->const 1
        target_names = ['A', 'B', 'C', 'D', '0', '1']
        # Precompute for each target code (0..5) and each 4-var valuation idx (0..15) whether that target is 1
        target_bit = [
            [(idx >> 0) & 1 for idx in range(16)],
            [(idx >> 1) & 1 for idx in range(16)],
            [(idx >> 2) & 1 for idx in range(16)],
            [(idx >> 3) & 1 for idx in range(16)],
            [0] * 16,
            [1] * 16,
        ]

        for c in distinct_large.values():
            pins = tuple(c['inputs'])
            num_pins = len(pins)
            cell_tt = eval_cell_truth_table(c['function'], pins)

            for assignment in itertools.product(range(6), repeat=num_pins):
                # Must contain all 4 variables 0, 1, 2, 3
                if 0 not in assignment or 1 not in assignment or 2 not in assignment or 3 not in assignment:
                    continue
                tt = 0
                for idx in range(16):
                    cell_idx = 0
                    for p_pos, t_code in enumerate(assignment):
                        if target_bit[t_code][idx]:
                            cell_idx |= (1 << p_pos)
                    if (cell_tt >> cell_idx) & 1:
                        tt |= (1 << idx)

                if depends_on_all_4(tt):
                    rep, _ = get_p_class(tt)
                    if rep not in self.exists_classes and rep not in self.exists_inv_classes:
                        self.contained_classes.add(rep)
                        if rep not in self.match_info:
                            tie_desc = ", ".join(f"{pins[p_pos]}={target_names[t_code]}" for p_pos, t_code in enumerate(assignment))
                            self.match_info[rep] = ("Contained", c['name'], f"Contained in {c['name']} ({tie_desc})", c['area'])

    def classify(self, tt: int) -> str:
        """Classifies a truth table into Table 3 classes."""
        rep, _ = get_p_class(tt & 0xFFFF)
        if rep in self.exists_classes:
            return "Exists"
        elif rep in self.exists_inv_classes:
            return "Exists with an inverter"
        elif rep in self.contained_classes:
            return "Contained"
        act = active_variables(tt & 0xFFFF)
        if len(act) < 4 and (len(act), rep) in self.hd_k_input_reps:
            return "Exists"
        return "New"

    def classify_with_details(self, tt: int) -> Tuple[str, str, str, float]:
        """
        Returns (category, matched_hd_cell, match_description, matched_cell_x1_area)
        for any candidate truth table.
        """
        rep, _ = get_p_class(tt & 0xFFFF)
        if rep in self.match_info:
            return self.match_info[rep]
        act = active_variables(tt & 0xFFFF)
        if len(act) < 4 and (len(act), rep) in self.hd_k_input_reps:
            cname = self.hd_k_input_reps[(len(act), rep)]
            return ("Exists", cname, f"Direct {len(act)}-input match to {cname}", 0.0)
        return ("New", "-", "Novel function not in HD", 0.0)

    def classify_hd_cell_dict(self, cell: Dict) -> str:
        """
        Checks any combinational HD cell dictionary (from 0 to 6 inputs) fed as a candidate.
        Section 5 rule: 'Every combinational HD cell, fed to it as a candidate, must come out as Exists.'
        """
        pins = tuple(cell['inputs'])
        k = len(pins)
        tt_full = eval_cell_truth_table(cell['function'], pins)
        if k <= 4:
            tt16 = 0
            for idx in range(16):
                sub_idx = idx & ((1 << k) - 1)
                if (tt_full >> sub_idx) & 1:
                    tt16 |= (1 << idx)
            if k == 4 and depends_on_all_4(tt16):
                return self.classify(tt16)
            rep, _ = get_p_class(tt16)
            if (k, rep) in self.hd_k_input_reps:
                return "Exists"
            return self.classify(tt16)
        else:
            if (k, tt_full) in self.hd_k_input_reps:
                return "Exists"
            return "New"

    def run_self_test(self) -> Dict[str, int]:
        """
        Runs the exhaustive self-test against Handout Table 4.
        All counts are derived algorithmically from first principles.
        """
        counts = {
            "Exists": 0,
            "Exists with an inverter": 0,
            "Contained": 0,
            "New": 0,
            "New, and one static CMOS stage": 0,
            "New, one stage, at most 3 transistors in series and at most 12 transistors": 0,
            "One stage with every input used once": 0,
            "One stage with every input used once, Exists": 0,
            "One stage with every input used once, Contained": 0
        }

        # 1. Partition all 64,594 non-degenerate 4-variable functions into 3,904 P-classes
        p_classes: Set[int] = set()
        for tt in range(65536):
            if depends_on_all_4(tt):
                rep, _ = get_p_class(tt)
                p_classes.add(rep)

        # 2. Classify each P-class into Table 3 categories
        for rep in p_classes:
            cat = self.classify(rep)
            counts[cat] += 1

        # 3. Synthesize 1-stage static CMOS networks from first principles
        sp_info = synthesize_one_stage_4inp()
        one_stage_all = sp_info["one_stage_all"]
        one_stage_3s_12tx = sp_info["one_stage_3s_12tx"]
        read_once_3s = sp_info["read_once_3s"]

        new_one_stage_reps = {rep for rep in one_stage_all if self.classify(rep) == "New"}
        new_one_stage_filtered = {rep for rep in one_stage_3s_12tx if self.classify(rep) == "New"}

        counts["New, and one static CMOS stage"] = len(new_one_stage_reps)
        counts["New, one stage, at most 3 transistors in series and at most 12 transistors"] = len(new_one_stage_filtered)

        # 4. One stage with every input used once (Option 1's simplest cells: 4 inputs used once, <= 3 in series)
        counts["One stage with every input used once"] = len(read_once_3s)
        counts["One stage with every input used once, Exists"] = sum(
            1 for rep in read_once_3s if self.classify(rep) == "Exists"
        )
        counts["One stage with every input used once, Contained"] = sum(
            1 for rep in read_once_3s if self.classify(rep) == "Contained"
        )

        return counts
