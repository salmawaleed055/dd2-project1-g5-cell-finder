"""
Worst delay of a mapped netlist with OpenSTA (Option 2 handout, section 7:
"report the worst delay from OpenSTA for each design").

The same constraints are used for every netlist, so baseline and extended
mappings are compared fairly:

  * every top-level input that drives a flip-flop clock pin gets a 10 ns
    clock (the period only sets the slack, not the arrival times);
  * every other input arrives at time 0 with that clock, every output is
    required at the clock edge with no external delay;
  * input transitions and output loads are OpenSTA's defaults (ideal inputs,
    no load beyond the fanout pins).

The reported number is the data arrival time of the worst max-delay path
(`report_checks -path_delay max`), i.e. the critical path through the
logic.  A purely combinational design has no clock; its worst path is taken
from `report_checks -unconstrained`.

New cells with estimated areas carry the placeholder scalar timing written by
src/liberty_writer.py, so their delays are as rough as those placeholders.
OpenSTA runs either as `sta` or inside `openroad`; STA_BIN overrides both.
"""

import os
import re
import shutil
from collections import Counter
from typing import Dict, List, Optional

from src.runner import runner

PERIOD_NS = 10.0
_SEARCH = ["~/eda-sta/bin", "/opt/OpenSTA/bin", "/usr/local/bin", "~/.local/bin"]


def find_sta() -> Optional[List[str]]:
    """Command line prefix that runs a Tcl file in OpenSTA, or None."""
    if os.environ.get("STA_BIN"):
        return [os.environ["STA_BIN"], "-no_init", "-no_splash", "-exit"]
    for name, args in (("sta", ["-no_init", "-no_splash", "-exit"]),
                       ("openroad", ["-no_init", "-no_splash", "-exit"])):
        path = shutil.which(name)
        if not path:
            for d in _SEARCH:
                cand = os.path.join(os.path.expanduser(d), name)
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    path = cand
                    break
        if path:
            return [path] + args
    return None


def clock_ports(netlist_text: str) -> List[str]:
    """Top-level inputs connected to a flip-flop CLK pin, most used first."""
    inputs = set()
    for decl in re.findall(r'^\s*input\s+(?:\[[^\]]*\]\s*)?([^;]+);', netlist_text, re.M):
        inputs.update(n.strip() for n in decl.split(','))
    nets = Counter(re.findall(r'\.CLK\(\s*([^\s)]+)\s*\)', netlist_text))
    return [n for n, _ in nets.most_common() if n in inputs]


def worst_delay(netlist: str, top: str, lib: str, work: str) -> Dict:
    """Runs OpenSTA on one netlist; returns {arrival_ns, slack_ns, clocks, log}."""
    sta = find_sta()
    if sta is None:
        return {"arrival_ns": None, "slack_ns": None, "clocks": [], "log": "OpenSTA not found"}
    os.makedirs(work, exist_ok=True)
    with open(netlist, 'r', encoding='utf-8') as f:
        clocks = clock_ports(f.read())
    tcl = [f"read_liberty {lib}", f"read_verilog {netlist}", f"link_design {top}"]
    if clocks:
        for i, c in enumerate(clocks):
            tcl.append(f"create_clock -name clk{i} -period {PERIOD_NS} [get_ports {{{c}}}]")
        clk_list = " ".join("{" + c + "}" for c in clocks)
        tcl += [f"set_input_delay 0 -clock clk0 [delete_from_list [all_inputs] [get_ports {{{clk_list}}}]]",
                "set_output_delay 0 -clock clk0 [all_outputs]",
                "report_checks -path_delay max -digits 4"]
    else:
        tcl.append("report_checks -unconstrained -path_delay max -digits 4")
    base = os.path.splitext(os.path.basename(netlist))[0]
    script = os.path.join(work, f"{base}.tcl").replace("\\", "/")
    with open(script, 'w', encoding='utf-8') as f:
        f.write("\n".join(tcl) + "\n")
    res = runner.run_cmd(sta + [script])
    out = res.stdout + res.stderr
    with open(os.path.join(work, f"{base}.sta.log"), 'w', encoding='utf-8') as f:
        f.write(out)
    # OpenSTA prints the worst path of every path group.  The asynchronous
    # group holds reset recovery/removal checks, not logic paths, so it is
    # skipped; the worst delay is the latest arrival over the other groups.
    worst = None
    for path in out.split("Startpoint:")[1:]:
        group = re.search(r'Path Group:\s*(\S+)', path)
        if group and group.group(1) == "asynchronous":
            continue
        arr = re.search(r'^\s*(-?[0-9.]+)\s+data arrival time', path, re.M)
        slack = re.search(r'^\s*(-?[0-9.]+)\s+slack', path, re.M)
        if arr and (worst is None or float(arr.group(1)) > worst[0]):
            worst = (float(arr.group(1)), float(slack.group(1)) if slack else None)
    return {"arrival_ns": worst[0] if worst else None,
            "slack_ns": worst[1] if worst else None,
            "clocks": clocks, "log": out[-1500:]}
