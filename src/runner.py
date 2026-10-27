"""
Cross-Platform EDA Tool Execution Engine
Abstracts execution of Yosys, ABC, AIG tools, and Icarus Verilog across:
- Native Linux (Ubuntu, Debian, Fedora, Arch)
- macOS (Homebrew / OSS CAD Suite)
- Linux container / WSL environment
- Windows host with native EDA tools or dynamic WSL bridge
"""

import os
import sys
import shutil
import subprocess
import re
from typing import List, Optional, Dict, Tuple


def is_windows() -> bool:
    return os.name == "nt"


def to_posix_path(path: str) -> str:
    """Converts a Windows path to a POSIX-style path."""
    return os.path.abspath(path).replace("\\", "/")


def get_wsl_path(path: str) -> str:
    """Dynamically converts a Windows path to a WSL /mnt/ path without hardcoding."""
    posix = to_posix_path(path)
    if len(posix) >= 2 and posix[1] == ":":
        drive = posix[0].lower()
        return f"/mnt/{drive}{posix[2:]}"
    return posix


class EDARunner:
    """
    Locates and runs EDA tools in a cross-platform, reproducible manner.
    """
    def __init__(self):
        self._tool_cache: Dict[str, Optional[str]] = {}
        self._use_wsl_bridge = False
        self._detect_environment()

    def _detect_environment(self):
        # 1. On POSIX (Linux, macOS, WSL shell): always run native tools directly
        if not is_windows():
            self._use_wsl_bridge = False
            return

        # 2. On Windows: check if native Windows binaries exist in PATH
        native_yosys = shutil.which("yosys") or shutil.which("yosys.exe")
        if native_yosys:
            self._use_wsl_bridge = False
        else:
            # Check if WSL is available to bridge Linux EDA tools
            wsl_bin = shutil.which("wsl") or shutil.which("wsl.exe")
            if wsl_bin:
                self._use_wsl_bridge = True
            else:
                self._use_wsl_bridge = False

    def find_tool(self, tool_name: str) -> Optional[str]:
        """
        Finds the executable path for tool_name.
        Honors environment variable overrides: e.g. YOSYS_BIN, ABC_BIN, AIGTOAIG_BIN.
        """
        env_var = f"{tool_name.upper().replace('-', '_')}_BIN"
        if env_var in os.environ:
            return os.environ[env_var]

        # Aliases
        if tool_name == "abc":
            for alias in ["yosys-abc", "abc"]:
                found = shutil.which(alias)
                if found:
                    return found
        else:
            found = shutil.which(tool_name)
            if found:
                return found

        # Standard Unix / Homebrew / OSS CAD paths if not in PATH
        search_dirs = [
            "/opt/oss-cad-suite/bin",
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            os.path.expanduser("~/oss-cad-suite/bin"),
            os.path.expanduser("~/.local/bin")
        ]
        for d in search_dirs:
            candidate = os.path.join(d, tool_name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

        return tool_name  # Fallback to name in PATH

    def run_cmd(self, cmd_args: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Runs a command transparently on the host or through the WSL bridge if on Windows.
        """
        work_dir = cwd or os.getcwd()

        if not self._use_wsl_bridge:
            # Native Linux, macOS, or native Windows
            return subprocess.run(
                cmd_args,
                cwd=work_dir,
                capture_output=True,
                text=True,
                env=os.environ.copy()
            )

        # Windows with WSL fallback
        wsl_work_dir = get_wsl_path(work_dir)
        # Build command string for WSL bash
        # Setup PATH inside WSL to check standard locations dynamically ($HOME/oss-cad-suite/bin, /opt/oss-cad-suite/bin, etc.)
        cmd_escaped = " ".join(f'"{arg}"' if " " in arg or ";" in arg else arg for arg in cmd_args)
        wsl_bash_script = (
            'export PATH="$HOME/oss-cad-suite/bin:/opt/oss-cad-suite/bin:$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH" && '
            f'cd "{wsl_work_dir}" && '
            f'{cmd_escaped}'
        )
        return subprocess.run(
            ["wsl", "--", "bash", "-c", wsl_bash_script],
            capture_output=True,
            text=True
        )

    def run_yosys_script(self, script_content: str, script_filename: str = "temp_syn.ys", cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Writes a Yosys script file and executes yosys -q <file>.
        """
        work_dir = cwd or os.getcwd()
        build_dir = os.path.join(work_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        script_path = os.path.join(build_dir, script_filename)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content + "\n")

        rel_script = os.path.join("build", script_filename).replace("\\", "/")
        return self.run_cmd(["yosys", "-q", rel_script], cwd=work_dir)

    def run_abc_script(self, abc_commands: str, script_filename: str = "temp_abc.script", cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Writes an ABC command file and executes yosys-abc -f <file>.
        """
        work_dir = cwd or os.getcwd()
        build_dir = os.path.join(work_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        script_path = os.path.join(build_dir, script_filename)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(abc_commands + "\n")

        rel_script = os.path.join("build", script_filename).replace("\\", "/")
        # Prefer yosys-abc, fallback to abc
        return self.run_cmd(["yosys-abc", "-f", rel_script], cwd=work_dir)

    def run_aigtoaig(self, src_aig: str, dest_aag: str, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Converts between binary and ASCII AIGER using aigtoaig.
        """
        src_clean = src_aig.replace("\\", "/")
        dest_clean = dest_aag.replace("\\", "/")
        return self.run_cmd(["aigtoaig", src_clean, dest_clean], cwd=cwd)

    def run_map_script(self, v_file: str, top: str, lib_file: str, script_opt: str, sv_flag: str = "", cwd: Optional[str] = None) -> float:
        """
        Executes map.sh and extracts chip area.
        Works across native Linux, macOS, and Windows.
        """
        map_sh = "given/scripts/map.sh"
        if not os.path.exists(map_sh) and os.path.exists(os.path.join("..", map_sh)):
            map_sh = os.path.join("..", map_sh)
        map_sh = map_sh.replace("\\", "/")

        v_clean = v_file.replace("\\", "/")
        lib_clean = lib_file.replace("\\", "/")

        args = ["bash", map_sh, v_clean, top, lib_clean, script_opt]
        if sv_flag:
            args.append(sv_flag.strip())

        res = self.run_cmd(args, cwd=cwd)
        if res.returncode != 0:
            raise RuntimeError(f"map.sh failed ({res.returncode}):\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")

        match = re.search(r"Chip area.*?:\s*([0-9.]+)", res.stdout)
        if not match:
            raise ValueError(f"Could not parse Chip area from output:\n{res.stdout}")
        return float(match.group(1))


    def can_execute_tools(self) -> bool:
        """Returns True if Yosys can be executed in the current runtime environment."""
        try:
            res = self.run_cmd(["yosys", "-V"])
            return res.returncode == 0
        except Exception:
            return False

    def check_environment(self) -> bool:
        """
        Validates all tools, libraries, and environment prerequisites across platforms.
        """
        print("=== Checking EDA Tools and Environment ===")
        import platform
        print(f"Host OS: {platform.system()} {platform.release()} ({platform.machine()})")
        print(f"Python: {sys.version.split()[0]}")
        if self._use_wsl_bridge:
            print("Execution mode: Windows host with automated WSL bridge")
        else:
            print("Execution mode: Native POSIX environment (Linux / macOS / container)")

        all_ok = True

        # Check Yosys
        res_yosys = self.run_cmd(["yosys", "-V"])
        if res_yosys.returncode == 0:
            print(f"  [OK] Yosys: {res_yosys.stdout.strip()}")
        else:
            print(f"  [FAIL] Yosys not found or returned error ({res_yosys.returncode})")
            all_ok = False

        # Check yosys-abc / abc
        res_abc = self.run_cmd(["yosys-abc", "-c", "version"])
        if res_abc.returncode != 0:
            res_abc = self.run_cmd(["abc", "-c", "version"])
        if res_abc.returncode == 0:
            abc_ver = res_abc.stdout.strip().splitlines()[0] if res_abc.stdout.strip() else "available"
            print(f"  [OK] ABC: {abc_ver}")
        else:
            print("  [FAIL] ABC (yosys-abc or abc) not found")
            all_ok = False

        # Check aigtoaig
        res_aig = self.run_cmd(["aigtoaig", "-h"])
        if res_aig.returncode == 0 or "usage" in (res_aig.stdout + res_aig.stderr).lower():
            print("  [OK] aigtoaig: available")
        else:
            print("  [FAIL] aigtoaig not found")
            all_ok = False

        # Check Icarus Verilog
        res_iverilog = self.run_cmd(["iverilog", "-V"])
        if res_iverilog.returncode == 0:
            iv_ver = res_iverilog.stdout.strip().splitlines()[0]
            print(f"  [OK] Icarus Verilog: {iv_ver}")
        else:
            print("  [WARN] Icarus Verilog not found (optional for gate simulation)")

        # Check libraries
        for lib in ["given/hd_reduced.lib", "given/hd_usable.lib"]:
            found = os.path.exists(lib) or os.path.exists(os.path.join("..", lib))
            if found:
                print(f"  [OK] Library: {lib} found")
            else:
                print(f"  [FAIL] Library: {lib} missing")
                all_ok = False

        return all_ok


# Global runner instance
runner = EDARunner()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "check":
        ok = runner.check_environment()
        sys.exit(0 if ok else 1)
    else:
        runner.check_environment()
