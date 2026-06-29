import os
import sys
import subprocess
import time
import statistics
import shutil
from dataclasses import dataclass, field
from typing import Optional

_ENERGY_SCALE = 1_000_000_000
_TIME_SCALE = 1_000
_DEFAULT_RUNS = 5
_MIN_MEANINGFUL_PCT = 0.5


@dataclass
class AuditReport:
    energy_before_kwh: float = 0.0
    energy_after_kwh: float = 0.0
    co2_before_kgco2eq: float = 0.0
    co2_after_kgco2eq: float = 0.0
    time_before_sec: float = 0.0
    time_after_sec: float = 0.0
    energy_confidence: str = "unknown"  # "high", "medium", "low", "unknown"
    time_confidence: str = "unknown"

    @property
    def energy_reduction_kwh(self) -> float:
        return self.energy_before_kwh - self.energy_after_kwh

    @property
    def co2_reduction_kgco2eq(self) -> float:
        return self.co2_before_kgco2eq - self.co2_after_kgco2eq

    @property
    def energy_reduction_pct(self) -> float:
        if self.energy_before_kwh == 0:
            return 0.0
        return (self.energy_reduction_kwh / self.energy_before_kwh) * 100

    @property
    def co2_reduction_pct(self) -> float:
        if self.co2_before_kgco2eq == 0:
            return 0.0
        return (self.co2_reduction_kgco2eq / self.co2_before_kgco2eq) * 100

    @property
    def time_reduction_sec(self) -> float:
        return self.time_before_sec - self.time_after_sec

    @property
    def time_reduction_pct(self) -> float:
        if self.time_before_sec == 0:
            return 0.0
        return (self.time_reduction_sec / self.time_before_sec) * 100

    def format_report(self) -> str:
        lines = [
            "=" * 50,
            "         CARBON AUDIT REPORT",
            "=" * 50,
            "",
            f"  Energy Before : {self.energy_before_kwh:.10f} kWh",
            f"  Energy After  : {self.energy_after_kwh:.10f} kWh",
            f"  Energy Saved  : {self.energy_reduction_kwh:.10f} kWh ({self.energy_reduction_pct:.2f}%)",
            f"  Confidence    : {self.energy_confidence.upper()}",
            "",
            f"  Time Before   : {self.time_before_sec:.10f} sec",
            f"  Time After    : {self.time_after_sec:.10f} sec",
            f"  Time Saved    : {self.time_reduction_sec:.10f} sec ({self.time_reduction_pct:.2f}%)",
            f"  Confidence    : {self.time_confidence.upper()}",
            "",
            f"  CO\u2082 Before    : {self.co2_before_kgco2eq:.10f} kgCO2eq",
            f"  CO\u2082 After     : {self.co2_after_kgco2eq:.10f} kgCO2eq",
            f"  CO\u2082 Saved     : {self.co2_reduction_kgco2eq:.10f} kgCO2eq ({self.co2_reduction_pct:.2f}%)",
            "",
            "=" * 50,
        ]
        return "\n".join(lines)


_MEASUREMENT_SCRIPT_TEMPLATE = '''\
import sys
import time
from codecarbon import OfflineEmissionsTracker

SAFE_BUILTINS = {{
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}}

run_energies = []
run_emissions = []
run_times = []

# Warm up Python and the tracker once so startup cost does not skew the measurements.
tracker = OfflineEmissionsTracker(
    country_iso_code="IND",
    log_level="error",
    save_to_file=False,
)
tracker.start()
start_time = time.perf_counter()
sandbox_globals = {{"__builtins__": SAFE_BUILTINS, "__name__": "__main__"}}
exec(compile({code}, "<target>", "exec"), sandbox_globals, sandbox_globals)
time_elapsed = time.perf_counter() - start_time
tracker.stop()

for _ in range({runs}):
    tracker = OfflineEmissionsTracker(
        country_iso_code="IND",
        log_level="error",
        save_to_file=False,
    )
    tracker.start()

    # ---- execute the target code ----
    start_time = time.perf_counter()
    sandbox_globals = {{"__builtins__": SAFE_BUILTINS, "__name__": "__main__"}}
    exec(compile({code}, "<target>", "exec"), sandbox_globals, sandbox_globals)
    time_elapsed = time.perf_counter() - start_time
    # ---- end target code ----

    emissions = tracker.stop()  # returns kgCO2eq
    energy = tracker._total_energy.kWh  # energy in kWh

    run_energies.append(energy)
    run_emissions.append(emissions)
    run_times.append(time_elapsed)

# Print individual runs
for energy in run_energies:
    print(f"ENERGY:{{energy}}")
for emission in run_emissions:
    print(f"EMISSION:{{emission}}")
for time_val in run_times:
    print(f"TIME:{{time_val}}")
'''


def _run_and_measure(code: str) -> tuple[float, float, float, list[float], list[float]]:
    """
    Execute *code* in a subprocess with CodeCarbon tracking.

    Returns:
        (energy_kwh_avg, co2_kgco2eq_avg, time_sec_avg, energy_runs, time_runs)
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", _MEASUREMENT_SCRIPT_TEMPLATE.format(code=repr(code), runs=_DEFAULT_RUNS)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if stderr:
                print(f"  [audit warning] {stderr[:200]}", file=sys.stderr)
            return 0.0, 0.0, 0.0, [], []

        output_lines = result.stdout.strip().splitlines()
        
        # Parse ENERGY: lines
        energy_runs = []
        for line in output_lines:
            if line.startswith("ENERGY:"):
                try:
                    energy_runs.append(float(line.split(":", 1)[1]))
                except (ValueError, IndexError):
                    pass
        
        # Parse EMISSION: lines
        emission_runs = []
        for line in output_lines:
            if line.startswith("EMISSION:"):
                try:
                    emission_runs.append(float(line.split(":", 1)[1]))
                except (ValueError, IndexError):
                    pass
        
        # Parse TIME: lines
        time_runs = []
        for line in output_lines:
            if line.startswith("TIME:"):
                try:
                    time_runs.append(float(line.split(":", 1)[1]))
                except (ValueError, IndexError):
                    pass
        
        if not energy_runs or not emission_runs or not time_runs:
            return 0.0, 0.0, 0.0, [], []
        
        # Median is less sensitive to occasional spikes from OS/background noise.
        energy_avg = statistics.median(energy_runs)
        co2_avg = statistics.median(emission_runs)
        time_avg = statistics.median(time_runs)
        
        return energy_avg, co2_avg, time_avg, energy_runs, time_runs

    except (subprocess.TimeoutExpired, ValueError, IndexError):
        return 0.0, 0.0, 0.0, [], []


_JS_MEASUREMENT_SCRIPT_TEMPLATE = '''\
import subprocess
import sys
import time
from codecarbon import OfflineEmissionsTracker

run_energies = []
run_emissions = []
run_times = []

node_cmd = {node_cmd}
target_code = {code}

# Warm-up run
tracker = OfflineEmissionsTracker(
    country_iso_code="IND",
    log_level="error",
    save_to_file=False,
)
tracker.start()
start_time = time.perf_counter()
subprocess.run(node_cmd + ["-e", target_code], check=True, capture_output=True, text=True)
time_elapsed = time.perf_counter() - start_time
tracker.stop()

for _ in range({runs}):
    tracker = OfflineEmissionsTracker(
        country_iso_code="IND",
        log_level="error",
        save_to_file=False,
    )
    tracker.start()

    start_time = time.perf_counter()
    subprocess.run(node_cmd + ["-e", target_code], check=True, capture_output=True, text=True)
    time_elapsed = time.perf_counter() - start_time

    emissions = tracker.stop()
    energy = tracker._total_energy.kWh

    run_energies.append(energy)
    run_emissions.append(emissions)
    run_times.append(time_elapsed)

for energy in run_energies:
    print(f"ENERGY:{{energy}}")
for emission in run_emissions:
    print(f"EMISSION:{{emission}}")
for time_val in run_times:
    print(f"TIME:{{time_val}}")
'''


def _run_and_measure_js(code: str) -> tuple[float, float, float, list[float], list[float]]:
    node_path = shutil.which("node")
    if not node_path:
        print("  [audit warning] Node.js not found; skipping JavaScript carbon audit", file=sys.stderr)
        return 0.0, 0.0, 0.0, [], []

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                _JS_MEASUREMENT_SCRIPT_TEMPLATE.format(
                    node_cmd=repr([node_path]),
                    code=repr(code),
                    runs=_DEFAULT_RUNS,
                ),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if stderr:
                print(f"  [audit warning] {stderr[:200]}", file=sys.stderr)
            return 0.0, 0.0, 0.0, [], []

        output_lines = result.stdout.strip().splitlines()

        energy_runs = []
        emission_runs = []
        time_runs = []

        for line in output_lines:
            if line.startswith("ENERGY:"):
                try:
                    energy_runs.append(float(line.split(":", 1)[1]))
                except (ValueError, IndexError):
                    pass
            elif line.startswith("EMISSION:"):
                try:
                    emission_runs.append(float(line.split(":", 1)[1]))
                except (ValueError, IndexError):
                    pass
            elif line.startswith("TIME:"):
                try:
                    time_runs.append(float(line.split(":", 1)[1]))
                except (ValueError, IndexError):
                    pass

        if not energy_runs or not emission_runs or not time_runs:
            return 0.0, 0.0, 0.0, [], []

        energy_avg = statistics.median(energy_runs)
        co2_avg = statistics.median(emission_runs)
        time_avg = statistics.median(time_runs)
        return energy_avg, co2_avg, time_avg, energy_runs, time_runs

    except (subprocess.TimeoutExpired, ValueError, IndexError):
        return 0.0, 0.0, 0.0, [], []


def _calculate_confidence(values: list[float]) -> str:
    """
    Calculate confidence level based on coefficient of variation.
    
    Returns:
        "high" if CV < 5%, "medium" if CV < 15%, "low" if CV >= 15%, "unknown" if no data
    """
    if not values or len(values) < 2:
        return "unknown"
    
    try:
        mean = statistics.mean(values)
        if mean == 0:
            return "unknown"
        
        stdev = statistics.stdev(values)
        cv = (stdev / mean) * 100  # Coefficient of Variation
        
        if cv < 5:
            return "high"
        elif cv < 15:
            return "medium"
        else:
            return "low"
    except (statistics.StatisticsError, ValueError):
        return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_audit(original_code: str, optimized_code: str, language: str = "python") -> AuditReport:
    
    report = AuditReport()

    run_measure = _run_and_measure if language == "python" else _run_and_measure_js

    print("  Running carbon audit on original code ...")
    energy_before, co2_before, time_before, energy_before_runs, time_before_runs = run_measure(original_code)
    report.energy_before_kwh = energy_before
    report.co2_before_kgco2eq = co2_before
    report.time_before_sec = time_before

    print("  Running carbon audit on optimized code ...")
    energy_after, co2_after, time_after, energy_after_runs, time_after_runs = run_measure(optimized_code)
    report.energy_after_kwh = energy_after
    report.co2_after_kgco2eq = co2_after
    report.time_after_sec = time_after
    
    # Calculate confidence levels from variance across runs
    # Combine before and after runs to get overall measurement stability
    all_energy_runs = energy_before_runs + energy_after_runs
    all_time_runs = time_before_runs + time_after_runs
    
    report.energy_confidence = _calculate_confidence(all_energy_runs)
    report.time_confidence = _calculate_confidence(all_time_runs)

    return report


def check_carbon_budget(emissions_after: float, budget: float) -> bool:
    return emissions_after <= budget


def check_audit_limits(
    energy_after: float,
    time_after: float,
    co2_after: float | None = None,
    carbon_budget: float | None = None,
    energy_budget: float | None = None,
    time_budget: float | None = None,
) -> dict[str, bool]:
    results: dict[str, bool] = {}

    if carbon_budget is not None and co2_after is not None:
        results["carbon"] = check_carbon_budget(co2_after, carbon_budget)

    if energy_budget is not None:
        results["energy"] = energy_after <= energy_budget

    if time_budget is not None:
        results["time"] = time_after <= time_budget

    return results


def _safe_reduction_pct(before: float, after: float, scale: float) -> float:
    if before <= 0:
        return 0.0

    if max(abs(before), abs(after)) < 1.0:
        before *= scale
        after *= scale

    reduction = ((before - after) / before) * 100
    if abs(reduction) < _MIN_MEANINGFUL_PCT:
        return 0.0
    return reduction


def calculate_combined_score(
    energy_before: float,
    energy_after: float,
    time_before: float,
    time_after: float,
) -> tuple[float, float, float]:
    energy_reduction_pct = _safe_reduction_pct(energy_before, energy_after, _ENERGY_SCALE)
    time_reduction_pct = _safe_reduction_pct(time_before, time_after, _TIME_SCALE)
    final_score = round((0.6 * energy_reduction_pct) + (0.4 * time_reduction_pct), 1)
    return energy_reduction_pct, time_reduction_pct, final_score


def calculate_green_rating(score: float) -> str:
    if score >= 40:
        return "⭐⭐⭐ Excellent"
    elif score >= 15:
        return "⭐⭐ Good"
    else:
        return "⭐ Poor"
