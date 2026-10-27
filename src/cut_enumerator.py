"""
4-Input Cut Enumerator and Exhaustive Simulation Verifier
References 10 and 11: DAG-aware AIG rewriting / priority cuts.
"""

import functools
import itertools
from typing import Dict, List, Tuple, Set, Optional
from src.aig import AIG, simulate_node


class CutVerificationError(Exception):
    """Raised when simulation of an AIG cut does not match its truth table."""
    pass


class Cut:
    def __init__(self, node: int, inputs: Tuple[int, ...], truth_table: int):
        self.node = node
        # Sorted tuple of cut input variable IDs
        self.inputs = tuple(sorted(inputs))
        # 16-bit canonical truth table representation
        self.truth_table = truth_table & 0xFFFF

    @property
    def size(self) -> int:
        return len(self.inputs)

    def __eq__(self, other) -> bool:
        return isinstance(other, Cut) and self.inputs == other.inputs and self.truth_table == other.truth_table

    def __hash__(self) -> int:
        return hash((self.inputs, self.truth_table))

    def __repr__(self) -> str:
        inps = ",".join(str(x) for x in self.inputs)
        return f"Cut(node={self.node}, inputs=({inps}), tt=0x{self.truth_table:04X})"


@functools.lru_cache(maxsize=None)
def _expand_tt_by_indices(src_tt: int, input_indices: Tuple[int, ...]) -> int:
    """Expands a 16-bit truth table from src positions to dest positions given by input_indices."""
    dest_tt = 0
    for dest_idx in range(16):
        src_idx = 0
        for s_pos, d_pos in enumerate(input_indices):
            if (dest_idx >> d_pos) & 1:
                src_idx |= (1 << s_pos)
        if (src_tt >> src_idx) & 1:
            dest_tt |= (1 << dest_idx)
    return dest_tt


def expand_tt_to_cut(src_tt: int, src_inputs: Tuple[int, ...], dest_inputs: Tuple[int, ...]) -> int:
    """
    Expands a truth table defined over src_inputs to dest_inputs (where src_inputs is a subset of dest_inputs).
    Both tuples are assumed sorted. Returns a 16-bit integer truth table.
    """
    if src_inputs == dest_inputs:
        return src_tt & 0xFFFF
    input_indices = tuple(dest_inputs.index(x) for x in src_inputs)
    return _expand_tt_by_indices(src_tt & 0xFFFF, input_indices)


class CutEnumerator:
    def __init__(self, aig: AIG, max_cut_size: int = 4, max_cuts_per_node: Optional[int] = None):
        self.aig = aig
        self.max_cut_size = max_cut_size
        self.max_cuts_per_node = max_cuts_per_node
        # node_id -> list of Cut objects
        self.cuts: Dict[int, List[Cut]] = {}

    def enumerate_cuts(self) -> Dict[int, List[Cut]]:
        """
        Enumerates all K-feasible cuts up to max_cut_size for all nodes in topological order.
        Always preserves the trivial cut Cut(var, (var,), 0xAAAA) at index 0 so downstream
        nodes can always treat any fanin node as a leaf.
        """
        # Leaves: Primary inputs and latches have only the trivial cut
        leaves = set(self.aig.inputs)
        for var, _ in self.aig.latches:
            leaves.add(var)

        for leaf in leaves:
            # Trivial cut: single input leaf. Variable 0 has mask 0xAAAA in 16-bit space
            self.cuts[leaf] = [Cut(leaf, (leaf,), 0xAAAA)]

        # Process AND nodes in topological order
        for var in self.aig.topo_order:
            lit0, lit1 = self.aig.and_nodes[var]
            var0 = AIG.lit_to_var(lit0)
            inv0 = AIG.lit_is_inverted(lit0)
            var1 = AIG.lit_to_var(lit1)
            inv1 = AIG.lit_is_inverted(lit1)

            cuts0 = self.cuts.get(var0, [])
            cuts1 = self.cuts.get(var1, [])

            # Collect candidate input sets -> (c0, c1)
            cand_pairs: Dict[Tuple[int, ...], Tuple[Cut, Cut]] = {}
            for c0 in cuts0:
                for c1 in cuts1:
                    merged_inputs = tuple(sorted(set(c0.inputs) | set(c1.inputs)))
                    if len(merged_inputs) <= self.max_cut_size and merged_inputs not in cand_pairs:
                        cand_pairs[merged_inputs] = (c0, c1)

            # Filter dominated cuts first: if sA is a strict subset of sB, sB is dominated
            sorted_input_sets = sorted(cand_pairs.keys(), key=lambda s: (len(s), s))
            non_dominated_sets: List[Tuple[int, ...]] = []
            non_dominated_fsets: List[Set[int]] = []

            for inp_tuple in sorted_input_sets:
                inp_set = set(inp_tuple)
                if not any(other_set.issubset(inp_set) for other_set in non_dominated_fsets):
                    non_dominated_sets.append(inp_tuple)
                    non_dominated_fsets.append(inp_set)

            # Compute exact truth table for each non-dominated cut
            non_dominated: List[Cut] = []
            for merged_inputs in non_dominated_sets:
                c0, c1 = cand_pairs[merged_inputs]
                tt0 = expand_tt_to_cut(c0.truth_table, c0.inputs, merged_inputs)
                if inv0:
                    tt0 = (~tt0) & 0xFFFF

                tt1 = expand_tt_to_cut(c1.truth_table, c1.inputs, merged_inputs)
                if inv1:
                    tt1 = (~tt1) & 0xFFFF

                merged_tt = (tt0 & tt1) & 0xFFFF
                non_dominated.append(Cut(var, merged_inputs, merged_tt))

            # Always place the trivial cut first so it is never truncated
            node_cut_list = [Cut(var, (var,), 0xAAAA)] + non_dominated
            if self.max_cuts_per_node is not None and self.max_cuts_per_node > 0:
                node_cut_list = node_cut_list[:self.max_cuts_per_node]

            self.cuts[var] = node_cut_list

        return self.cuts


def verify_cut(aig: AIG, cut: Cut) -> bool:
    """
    Checks the correctness of a cut by simulating the sub-AIG cone for all 2^k input valuations.
    Raises CutVerificationError if any input combination disagrees with the truth table.
    """
    k = len(cut.inputs)
    num_tests = 1 << k
    for idx in range(num_tests):
        assignment = {}
        for bit_pos, inp_var in enumerate(cut.inputs):
            assignment[inp_var] = (idx >> bit_pos) & 1

        sim_val = simulate_node(aig, cut.node, assignment)
        expected_val = (cut.truth_table >> idx) & 1
        if sim_val != expected_val:
            raise CutVerificationError(
                f"Cut simulation mismatch at node {cut.node} for inputs {cut.inputs}: "
                f"at test vector {idx:0{k}b}, simulated {sim_val} != expected {expected_val} "
                f"(cut TT: 0x{cut.truth_table:04X})"
            )
    return True
