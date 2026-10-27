"""
AIGER Parser and Data Structures
Supports ASCII AIGER format (.aag) for And-Inverter Graphs.
"""

from typing import Dict, List, Tuple, Set, Optional


class AIG:
    def __init__(self):
        self.max_var: int = 0
        self.num_inputs: int = 0
        self.num_latches: int = 0
        self.num_outputs: int = 0
        self.num_ands: int = 0

        self.inputs: List[int] = []  # variable IDs
        self.latches: List[Tuple[int, int]] = []  # (var_id, next_lit)
        self.outputs: List[int] = []  # output literals
        # and_nodes: var_id -> (lit0, lit1)
        self.and_nodes: Dict[int, Tuple[int, int]] = {}
        
        # Topological order of AND nodes
        self.topo_order: List[int] = []

    @staticmethod
    def lit_to_var(lit: int) -> int:
        return lit >> 1

    @staticmethod
    def lit_is_inverted(lit: int) -> bool:
        return bool(lit & 1)

    @staticmethod
    def var_to_lit(var: int, inverted: bool = False) -> int:
        return (var << 1) | (1 if inverted else 0)

    def is_input(self, var: int) -> bool:
        return var in self.inputs

    def is_latch(self, var: int) -> bool:
        return any(v == var for v, _ in self.latches)

    def is_and(self, var: int) -> bool:
        return var in self.and_nodes

    def compute_topo_order(self):
        """Topological ordering of AND nodes from leaves (inputs/latches) towards outputs."""
        visited: Set[int] = set(self.inputs)
        for var, _ in self.latches:
            visited.add(var)
        visited.add(0)  # constant 0

        order: List[int] = []

        def visit(var: int):
            if var in visited:
                return
            if var in self.and_nodes:
                lit0, lit1 = self.and_nodes[var]
                visit(AIG.lit_to_var(lit0))
                visit(AIG.lit_to_var(lit1))
                visited.add(var)
                order.append(var)

        for var in self.and_nodes:
            visit(var)

        self.topo_order = order


def parse_aag(filepath: str) -> AIG:
    """Parses an ASCII AIGER (.aag) file."""
    aig = AIG()
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    line_idx = 0
    header = lines[line_idx].strip().split()
    if header[0] != 'aag':
        raise ValueError(f"Expected 'aag' header in {filepath}, got {header[0]}")

    aig.max_var = int(header[1])
    aig.num_inputs = int(header[2])
    aig.num_latches = int(header[3])
    aig.num_outputs = int(header[4])
    aig.num_ands = int(header[5])
    line_idx += 1

    # Inputs: one lit per line (lit = 2 * var)
    for _ in range(aig.num_inputs):
        lit = int(lines[line_idx].strip())
        aig.inputs.append(AIG.lit_to_var(lit))
        line_idx += 1

    # Latches: var lit
    for _ in range(aig.num_latches):
        parts = lines[line_idx].strip().split()
        lit = int(parts[0])
        next_lit = int(parts[1]) if len(parts) > 1 else 0
        aig.latches.append((AIG.lit_to_var(lit), next_lit))
        line_idx += 1

    # Outputs: one lit per line
    for _ in range(aig.num_outputs):
        lit = int(lines[line_idx].strip())
        aig.outputs.append(lit)
        line_idx += 1

    # AND gates: lhs rhs0 rhs1
    for _ in range(aig.num_ands):
        parts = lines[line_idx].strip().split()
        lhs = int(parts[0])
        rhs0 = int(parts[1])
        rhs1 = int(parts[2])
        var = AIG.lit_to_var(lhs)
        aig.and_nodes[var] = (rhs0, rhs1)
        line_idx += 1

    aig.compute_topo_order()
    return aig


def simulate_node(aig: AIG, target_node: int, input_assignment: Dict[int, int]) -> int:
    """
    Simulates the sub-AIG between the given input assignments and target_node.
    input_assignment: maps variable ID -> 0 or 1.
    Evaluates intermediate AND nodes up to target_node.
    """
    values: Dict[int, int] = dict(input_assignment)
    values[0] = 0  # constant 0

    def get_lit_val(lit: int) -> int:
        var = AIG.lit_to_var(lit)
        if var not in values:
            if var in aig.and_nodes:
                evaluate_node(var)
            else:
                raise KeyError(f"Variable {var} not found in assignment or AND nodes")
        base = values[var]
        return 1 - base if AIG.lit_is_inverted(lit) else base

    def evaluate_node(var: int):
        if var in values:
            return
        lit0, lit1 = aig.and_nodes[var]
        v0 = get_lit_val(lit0)
        v1 = get_lit_val(lit1)
        values[var] = v0 & v1

    evaluate_node(target_node)
    return values[target_node]
