import cProfile
import ast
import io
import pstats
import shutil
import subprocess
from typing import Dict, List


def _profile_python_code(code_str: str, top_n: int = 5) -> List[Dict[str, float]]:
    """
    Profile Python code and return top hotspots by cumulative time.

    Returns:
        A list like: [{"function": "compute", "time": 0.002}, ...]
    """
    profiler = cProfile.Profile()

    # Gather user-defined function names so hotspots are meaningful.
    user_functions = set()
    try:
        parsed = ast.parse(code_str)
        for node in ast.walk(parsed):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                user_functions.add(node.name)
    except SyntaxError:
        return []

    # Isolated namespace to avoid leaking variables into app scope.
    exec_globals = {"__name__": "__main__"}
    exec_locals = {}

    try:
        profiler.enable()
        exec(compile(code_str, "<profiled_code>", "exec"), exec_globals, exec_locals)
        profiler.disable()
    except Exception:
        profiler.disable()
        return []

    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream)
    stats.sort_stats("cumulative")

    hotspots: List[Dict[str, float]] = []
    for func_key, values in stats.stats.items():
        # pstats tuple: (cc, nc, tt, ct, callers)
        cumulative_time = float(values[3])
        func_name = func_key[2]

        # Skip profiler internals and zero-time entries.
        if cumulative_time <= 0:
            continue
        if func_name in {"<built-in method builtins.exec>", "exec", "<method 'disable' of '_lsprof.Profiler' objects>"}:
            continue
        if func_name.startswith("<built-in") or func_name.startswith("<method"):
            continue

        # Keep only user-defined function hotspots.
        if func_name not in user_functions:
            continue

        hotspots.append({"function": func_name, "time": cumulative_time})

    hotspots.sort(key=lambda x: x["time"], reverse=True)
    return hotspots[: max(1, min(top_n, 5))]


def _profile_javascript_code(code_str: str, top_n: int = 5) -> List[Dict[str, float]]:
    node_path = shutil.which("node")
    if not node_path:
        return []

    wrapped_script = (
        "const __start = process.hrtime.bigint();\n"
        + code_str
        + "\nconst __elapsed = Number(process.hrtime.bigint() - __start) / 1e9;\n"
        + "console.log(`CTT_PROFILE_TOTAL:${__elapsed}`);\n"
    )

    try:
        result = subprocess.run(
            [node_path, "-e", wrapped_script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode != 0:
            return []

        for line in result.stdout.splitlines():
            if line.startswith("CTT_PROFILE_TOTAL:"):
                try:
                    total = float(line.split(":", 1)[1])
                    return [{"function": "<module>", "time": total}][: max(1, min(top_n, 5))]
                except ValueError:
                    return []
    except Exception:
        return []

    return []


def profile_code(code_str: str, top_n: int = 5, language: str = "python") -> List[Dict[str, float]]:
    if language == "python":
        return _profile_python_code(code_str, top_n=top_n)
    if language == "javascript":
        return _profile_javascript_code(code_str, top_n=top_n)
    return []
