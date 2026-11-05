"""
Real cells: reading cell responses (overview, Appendix A) and putting the
Liberty cell that comes back in place of the estimated entry (Option 2
handout, section 4, step 11).

A response is accepted only if every rule of Appendix A holds:

  * it answers one of our requests (same request_id and cell name);
  * status is "pass" (a cell whose status is not pass must not be used in
    a mapping);
  * the Liberty file it names exists and holds exactly one cell group, with
    the requested name, the requested input pins and output pin;
  * the output function, evaluated over all 16 input combinations, equals
    the requested truth table;
  * the area is positive and every input pin has a capacitance.

The function is evaluated with the parser below, which reads the full Liberty
operator set (!, ', &, *, juxtaposition, |, +, ^, 0, 1), not only the subset
HD uses, because the cell maker may write its functions differently.
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple

RESPONSE_DIR = "cells/responses"


# ---------------------------------------------------------------- functions
def _tokens(expr: str) -> List[str]:
    toks = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[01]|[!'&*|+^()]|\S", expr)
    for t in toks:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*|[01]|[!'&*|+^()]", t):
            raise ValueError(f"unknown token '{t}' in Liberty function '{expr}'")
    return toks


def eval_liberty(expr: str, values: Dict[str, int]) -> int:
    """
    Value (0 or 1) of a Liberty function for one input assignment.
    Precedence, highest first: ! and postfix ', then ^, then & * and
    juxtaposition, then | and +.
    """
    toks = _tokens(expr)
    pos = 0

    def peek() -> Optional[str]:
        return toks[pos] if pos < len(toks) else None

    def take() -> str:
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def primary() -> int:
        t = take()
        if t == '!':
            return 1 - primary()
        if t == '(':
            v = disjunction()
            if take() != ')':
                raise ValueError(f"unbalanced parentheses in '{expr}'")
        elif t in ('0', '1'):
            v = int(t)
        elif t in values:
            v = values[t]
        else:
            raise ValueError(f"pin '{t}' of '{expr}' is not an input")
        while peek() == "'":
            take()
            v = 1 - v
        return v

    def xor() -> int:
        v = primary()
        while peek() == '^':
            take()
            v ^= primary()
        return v

    def conjunction() -> int:
        v = xor()
        while peek() is not None and peek() not in ('|', '+', ')'):
            if peek() in ('&', '*'):
                take()
            v &= xor()
        return v

    def disjunction() -> int:
        v = conjunction()
        while peek() in ('|', '+'):
            take()
            v |= conjunction()
        return v

    v = disjunction()
    if pos != len(toks):
        raise ValueError(f"trailing tokens in '{expr}'")
    return v


def truth_table(expr: str, inputs: List[str]) -> int:
    """Truth table in the Appendix A order: input k of inputs is bit k of i."""
    return sum(1 << i for i in range(1 << len(inputs))
               if eval_liberty(expr, {p: (i >> k) & 1 for k, p in enumerate(inputs)}))


# ---------------------------------------------------------------- Liberty
def cell_groups(text: str) -> List[Tuple[str, str]]:
    """[(name, full text of the group)] of every cell group, by brace matching."""
    out = []
    for m in re.finditer(r'\bcell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)\s*\{', text):
        depth, i = 0, m.end() - 1
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append((m.group(1), text[m.start():i + 1]))
    return out


def _pin_groups(cell_text: str) -> Dict[str, str]:
    """{pin name: pin group text} of one cell group (nested braces allowed)."""
    pins = {}
    for m in re.finditer(r'\bpin\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)\s*\{', cell_text):
        depth, i = 0, m.end() - 1
        while i < len(cell_text):
            if cell_text[i] == '{':
                depth += 1
            elif cell_text[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        pins[m.group(1)] = cell_text[m.start():i + 1]
    return pins


def read_cell(cell_text: str) -> Dict:
    """Name, area, input pins (with capacitance), output pin and function of a cell group."""
    name = re.match(r'\s*cell\s*\(\s*"?([A-Za-z0-9_]+)', cell_text).group(1)
    area = re.search(r'\barea\s*:\s*([0-9.eE+-]+)', cell_text)
    cell = {"name": name, "area": float(area.group(1)) if area else 0.0,
            "inputs": [], "caps": {}, "outputs": {}}
    for pin, body in _pin_groups(cell_text).items():
        d = re.search(r'direction\s*:\s*"?(\w+)"?', body)
        if not d:
            continue
        if d.group(1) == "input":
            cell["inputs"].append(pin)
            cap = re.search(r'\bcapacitance\s*:\s*([0-9.eE+-]+)', body)
            cell["caps"][pin] = float(cap.group(1)) if cap else None
        elif d.group(1) == "output":
            fn = re.search(r'function\s*:\s*"([^"]+)"', body)
            cell["outputs"][pin] = fn.group(1) if fn else None
    return cell


# ---------------------------------------------------------------- responses
def check_response(resp: Dict, req: Dict, root: str = ".") -> Tuple[List[str], Optional[str]]:
    """
    Checks one response against its request.  Returns (problems, cell group
    text); the cell may be used only when problems is empty.
    """
    problems = []
    for key in ("request_id", "status", "cell", "files"):
        if key not in resp:
            problems.append(f"missing field '{key}'")
    if problems:
        return problems, None
    if resp["request_id"] != req["request_id"]:
        problems.append(f"request_id {resp['request_id']} does not answer {req['request_id']}")
    if resp["cell"] != req["name"]:
        problems.append(f"cell {resp['cell']} is not the requested {req['name']}")
    if resp["status"] != "pass":
        problems.append(f"status is {resp['status']} ({resp.get('reason')}), not pass")
        return problems, None
    lib_path = os.path.join(root, (resp.get("files") or {}).get("liberty") or "")
    if not os.path.isfile(lib_path):
        problems.append(f"Liberty file {lib_path} not found")
        return problems, None
    with open(lib_path, 'r', encoding='utf-8') as f:
        groups = cell_groups(f.read())
    if len(groups) != 1:
        problems.append(f"{lib_path} holds {len(groups)} cell groups, not exactly one")
        return problems, None
    name, text = groups[0]
    cell = read_cell(text)
    if name != req["name"]:
        problems.append(f"cell group is named {name}, not {req['name']}")
    if sorted(cell["inputs"]) != sorted(req["inputs"]):
        problems.append(f"input pins {cell['inputs']} are not {req['inputs']}")
    if list(cell["outputs"]) != [req["output"]]:
        problems.append(f"output pins {list(cell['outputs'])} are not ['{req['output']}']")
    elif not cell["outputs"][req["output"]]:
        problems.append("the output has no function attribute")
    else:
        try:
            tt = truth_table(cell["outputs"][req["output"]], req["inputs"])
            if tt != int(req["truth_table"], 16):
                problems.append(f"function '{cell['outputs'][req['output']]}' is 0x{tt:04X}, "
                                f"not the requested {req['truth_table']}")
        except ValueError as e:
            problems.append(str(e))
    if cell["area"] <= 0:
        problems.append("area is missing or not positive")
    missing_cap = [p for p, c in cell["caps"].items() if c is None]
    if missing_cap:
        problems.append(f"input pins without capacitance: {missing_cap}")
    return problems, (text if not problems else None)


def collect_real_cells(cells: List[Dict], req_dir: str = "cells/requests",
                       resp_dir: str = RESPONSE_DIR, root: str = ".") -> List[Dict]:
    """
    For every cell of the final set, the outcome of its response:
    {name, status: accepted | rejected | no response, problems, text, area}.
    """
    out = []
    for c in cells:
        rec = {"name": c["name"], "est_area": c["area"], "status": "no response",
               "problems": [], "text": None, "area": None, "response": None}
        req_path = os.path.join(root, req_dir, f"{c['name']}.json")
        resp_path = os.path.join(root, resp_dir, f"{c['name']}.json")
        if os.path.isfile(resp_path) and os.path.isfile(req_path):
            with open(req_path, 'r', encoding='utf-8') as f:
                req = json.load(f)
            with open(resp_path, 'r', encoding='utf-8') as f:
                resp = json.load(f)
            problems, text = check_response(resp, req, root)
            rec.update(response=resp_path, problems=problems, text=text,
                       status="accepted" if text else "rejected")
            if text:
                rec["area"] = read_cell(text)["area"]
        out.append(rec)
    return out


def write_real_liberty(base_lib: str, accepted: List[Dict], out_lib: str) -> None:
    """base_lib with the accepted real cell groups added inside its library group."""
    with open(base_lib, 'r', encoding='utf-8') as f:
        text = f.read()
    end = text.rstrip().rfind('}')
    groups = "\n".join(r["text"] for r in accepted)
    os.makedirs(os.path.dirname(out_lib) or ".", exist_ok=True)
    with open(out_lib, 'w', encoding='utf-8') as f:
        f.write(text[:end] + "\n  /* DD2 Project 1 group 5: new cells, real (from cell responses) */\n"
                + groups + "\n}\n")
