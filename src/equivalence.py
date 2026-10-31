"""
Equivalence check of a mapped netlist against its RTL with ABC `cec`
(Option 2 handout, section 4, step 9).

The reference ("gold") is the design right after `synth -flatten` and
`dfflibmap`, written in a separate Yosys run with the same commands (writing
it inside the mapping run renames signals and changes ABC's result), so both
sides have the same flip-flops.  Only `abc` and `opt_clean -purge` stand between gold and
gate, which is exactly the part that new cells change.

Both netlists are turned into AIGs the same way:
  * combinational HD and new cells get their function from the Liberty
    (`read_liberty -ignore_miss_func`);
  * flip-flop cells get a one-bit Verilog model generated from the Liberty ff
    group (Yosys's own Liberty import makes two state bits, IQ and IQ_N, per
    flip-flop, which ABC then cannot match);
  * async2sync; dffunmap; aigmap; write_aiger.
ABC's combinational `cec` pairs flip-flops by position, and `abc` plus
`opt_clean -purge` reorder them, so the check uses `dsec`, ABC's sequential
equivalence checker, which pairs only primary inputs and outputs (by port
order, which mapping keeps) and proves the flip-flops equivalent itself.
"""

import os
import re
from typing import Dict, List, Tuple

from src.runner import runner


def _expr_to_verilog(expr: str) -> str:
    """Liberty boolean expression -> Verilog expression."""
    return expr.replace('!', '~')


def write_ff_models(lib_path: str, out_path: str) -> List[str]:
    """
    Writes a Verilog model with a single state bit for every flip-flop cell of
    the Liberty file.  Returns the list of modelled cell names.
    Latches are not modelled: none of the required designs maps to one, and
    an unmodelled cell makes the check fail loudly instead of passing.
    """
    with open(lib_path, 'r', encoding='utf-8') as f:
        content = f.read()
    heads = list(re.finditer(r'\n\s*cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)', content))
    lines = ["// one-bit flip-flop models generated from " + os.path.basename(lib_path)]
    names = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(content)
        block = content[m.start():end]
        ff = re.search(r'\bff\s*\(([^)]*)\)\s*\{(.*?)\}', block, re.S)
        if not ff:
            continue
        attrs = dict(re.findall(r'(\w+)\s*:\s*"?([^";]+?)"?\s*;', ff.group(2)))
        pins = re.findall(
            r'\bpin\s*\(\s*"?(\w+)"?\s*\)\s*\{(.*?)\n\s{8}\}', block, re.S)
        inputs, outputs = [], []
        for pname, pbody in pins:
            d = re.search(r'direction\s*:\s*"?(\w+)"?', pbody)
            if not d:
                continue
            if d.group(1) == 'input':
                inputs.append(pname)
            else:
                fn = re.search(r'function\s*:\s*"([^"]+)"', pbody)
                outputs.append((pname, fn.group(1) if fn else 'IQ'))

        clk = attrs['clocked_on']
        clk_edge = f"negedge {clk[1:]}" if clk.startswith('!') else f"posedge {clk}"
        events = [clk_edge]
        body = []
        # Liberty: clear/preset are active when the expression is 1.
        for kind, value in (('clear', "1'b0"), ('preset', "1'b1")):
            if kind in attrs:
                e = attrs[kind]
                events.append(f"negedge {e[1:]}" if e.startswith('!') else f"posedge {e}")
                body.append((_expr_to_verilog(e), value))
        names.append(m.group(1))
        ports = inputs + [o for o, _ in outputs]
        lines.append(f"module {m.group(1)}({', '.join(ports)});")
        lines += [f"  input {p};" for p in inputs]
        lines += [f"  output {o};" for o, _ in outputs]
        lines.append("  reg IQ;")
        lines.append(f"  always @({' or '.join(events)})")
        stmt = "    "
        for cond, value in body:
            stmt += f"if ({cond}) IQ <= {value}; else "
        lines.append(stmt + f"IQ <= {_expr_to_verilog(attrs['next_state'])};")
        for o, fn in outputs:
            lines.append(f"  assign {o} = {_expr_to_verilog(fn).replace('IQ_N', '~IQ')};")
        lines.append("endmodule")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
    return names


def netlist_to_aig(netlist: str, top: str, lib_path: str, ff_models: str,
                   ff_cells: List[str], out_aig: str) -> None:
    """Turns a gate-level netlist into a sequential AIG (see module docstring)."""
    script = (
        f"read_liberty -ignore_miss_func {lib_path}\n"
        + "".join(f"delete {c}\n" for c in ff_cells)
        + f"read_verilog {ff_models}\n"
        f"read_verilog {netlist}\n"
        f"hierarchy -top {top}\n"
        "flatten\n"
        "proc\n"
        "async2sync\n"
        "simplemap\n"
        "dffunmap\n"
        "opt_clean\n"
        "aigmap\n"
        f"write_aiger {out_aig}\n"
    )
    res = runner.run_yosys_script(script, os.path.basename(out_aig) + ".ys")
    if res.returncode != 0 or not os.path.exists(out_aig):
        raise RuntimeError(f"AIG conversion of {netlist} failed:\n{res.stderr[-2000:]}")


def run_cec(gold_aig: str, gate_aig: str) -> Tuple[bool, str]:
    """Runs ABC `dsec` and returns (equivalent, ABC output)."""
    res = runner.run_cmd(["yosys-abc", "-c", f"dsec {gold_aig} {gate_aig}"])
    out = res.stdout + res.stderr
    return ("Networks are equivalent" in out and "NOT" not in out), out
