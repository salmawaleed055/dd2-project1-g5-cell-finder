"""
Repair of pin names in Yosys-mapped gate-level netlists.

With Yosys 0.70+190, `abc -liberty` sometimes reads ABC's mapped netlist back
with one input pin of a cell named after an internal signal instead of the
Liberty pin, for example

    sky130_fd_sc_hd__o311ai_1 _726_ ( .\\$abc$1524$new_n524 (_387_), .A1(...), ... );

where the pin should be `C1`.  Area is unaffected (it comes from the cell
type), but a netlist with such a pin cannot be checked for equivalence: the
real pin is left undriven.  Within one abc call a wrong name always stands for
the same Liberty pin, so the repair solves the mapping wrong-name -> pin from
instances where exactly one pin is missing, and propagates it.

The repair is never trusted on its own: every repaired netlist goes through
ABC `cec` against the RTL (src/equivalence.py), so a wrong repair is caught.
"""

import re
from typing import Dict, List, Tuple

# One cell instance as written by `write_verilog -noattr`.
_INST_RE = re.compile(r'\n  (\S+) (\S+) \((.*?)\n  \);', re.S)
# One port connection inside an instance, `.PIN(net)` or `.\escaped (net)`.
_PORT_RE = re.compile(r'\n    \.(.*?) ?\(')


def liberty_pins(lib_path: str) -> Dict[str, List[str]]:
    """Returns {cell name: [all pin names]} for every cell of a Liberty file."""
    with open(lib_path, 'r', encoding='utf-8') as f:
        content = f.read()
    heads = list(re.finditer(r'\n\s*cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)', content))
    pins: Dict[str, List[str]] = {}
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(content)
        block = content[m.start():end]
        pins[m.group(1)] = re.findall(r'\bpin\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)', block)
    return pins


def repair_netlist(netlist: str, pins: Dict[str, List[str]]) -> Tuple[str, Dict[str, str]]:
    """
    Renames every wrong port name to the Liberty pin it stands for.
    Returns (repaired netlist, {wrong name: pin}).  Raises ValueError if a
    wrong name cannot be resolved.
    """
    insts = []
    for m in _INST_RE.finditer(netlist):
        cell = m.group(1)
        if cell not in pins:
            continue
        ports = _PORT_RE.findall(m.group(3))
        insts.append((cell, ports))

    alias: Dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for cell, ports in insts:
            valid = set(pins[cell])
            wrong = [p for p in ports if p not in valid and p not in alias]
            if len(wrong) != 1:
                continue
            present = {alias.get(p, p) for p in ports}
            missing = [p for p in pins[cell] if p not in present]
            if len(missing) == 1:
                alias[wrong[0]] = missing[0]
                changed = True

        if changed:
            continue
        # Last resort: an instance whose wrong names all stand for its
        # missing pins, in any order.  They are assigned in pin order; this
        # is only correct when those pins are interchangeable (for example
        # C1 and D1 of o2111ai), and the equivalence check decides.
        for cell, ports in insts:
            wrong = [p for p in ports if p not in set(pins[cell]) and p not in alias]
            present = {alias.get(p, p) for p in ports}
            missing = [p for p in pins[cell] if p not in present]
            if wrong and len(wrong) == len(missing):
                alias.update(zip(wrong, missing))
                changed = True
                break

    unresolved = {p for cell, ports in insts for p in ports
                  if p not in set(pins[cell]) and p not in alias}
    if unresolved:
        raise ValueError(f"cannot resolve port names: {sorted(unresolved)}")

    def fix(m: re.Match) -> str:
        if m.group(1) not in pins:
            return m.group(0)
        # an escaped identifier ends with a space before '(', a plain one not
        valid = set(pins[m.group(1)])
        body = _PORT_RE.sub(
            lambda p: "\n    ." + (p.group(1) if p.group(1) in valid else alias[p.group(1)]) + "(",
            m.group(3))
        return f"\n  {m.group(1)} {m.group(2)} ({body}\n  );"

    return _INST_RE.sub(fix, netlist), alias
