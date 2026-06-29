import argparse
import sys
import time

from ctt.parser import parse_code, read_source, ParseError
from ctt.optimizer import optimize_ast
from ctt.optimizer_javascript import optimize_javascript_source
from ctt.code_generator import generate_code, generate_code_to_file
from ctt.carbon_audit import (
    run_audit,
    check_carbon_budget,
    calculate_green_rating,
    calculate_combined_score,
    check_audit_limits,
)
from ctt.profiler import profile_code
from ctt.utils import validate_file_with_language, print_section
from ctt.validator import validate_code_strict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ctt",
        description="Carbon-Track Transpiler — Analyze and optimize Python code for energy efficiency.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ---- analyze command ----
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a Python file, optimize it, and produce a carbon audit report.",
    )
    analyze_parser.add_argument(
        "file",
        help="Path to the source file to analyze (.py, .js, .mjs, .cjs).",
    )
    analyze_parser.add_argument(
        "--language",
        choices=["auto", "python", "javascript"],
        default="auto",
        help="Source language (default: auto-detect from extension).",
    )
    analyze_parser.add_argument(
        "--no-audit",
        action="store_true",
        default=False,
        help="Skip the carbon audit (energy measurement) step.",
    )
    analyze_parser.add_argument(
        "-o", "--output",
        default=None,
        help="Write the optimized code to this file.",
    )
    analyze_parser.add_argument(
        "--profile",
        action="store_true",
        default=False,
        help="Enable cProfile hotspot detection and optimize hotspot regions only.",
    )
    analyze_parser.add_argument(
        "--mode",
        choices=["energy", "general", "both"],
        default="both",
        help="Select optimization mode: energy, general, or both.",
    )
    analyze_parser.add_argument(
        "--budget",
        type=float,
        default=None,
        help="Optional carbon budget in kgCO2eq to compare after the audit.",
    )

    return parser


def run_analyze(args: argparse.Namespace) -> None:
    # 1. Validate input file
    file_path, language = validate_file_with_language(args.file, language=args.language)

    # 2. Read original source
    original_source = read_source(file_path)

    # 2a. Strict source validation
    is_valid, validation_msg = validate_code_strict(original_source, language=language)
    if not is_valid:
        print(f"\n❌ Validation Failed: {validation_msg}\n")
        sys.exit(1)
    print(f"✅ Input validation: {validation_msg}\n")

    hotspots = None
    if args.profile:
        print("Profiling source code ...")
        profile_start = time.perf_counter()
        hotspots = profile_code(original_source, language=language)
        profile_elapsed = time.perf_counter() - profile_start

        print("\n---- Profiling Summary ----")
        print("Top Hotspots:")
        if hotspots:
            for hotspot in hotspots:
                print(f"* {hotspot['function']} ({hotspot['time']:.6f}s)")
        else:
            print("* No hotspots detected (or profiling execution failed)")
        print(f"Profiling Time: {profile_elapsed:.4f}s\n")

    # 3. Parse AST
    print("Parsing source code ...")
    try:
        tree = parse_code(file_path, language=language)
    except ParseError as e:
        print(f"❌ Parse Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during parsing: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Optimize
    print("Applying optimizations ...")
    if language == "python":
        optimized_tree, records = optimize_ast(tree, mode=args.mode, hotspots=hotspots)
        optimized_source = generate_code(optimized_tree, language=language)
    else:
        optimized_source, records = optimize_javascript_source(original_source, mode=args.mode, hotspots=hotspots)
        optimized_tree = {"type": "Program", "language": "javascript", "source": optimized_source}

    # 5. Generate optimized code
    optimized_source = generate_code(optimized_tree, language=language)

    # 6. Display original and optimized code
    print(f"Optimization Mode: {args.mode}")
    if args.budget is not None:
        print(f"Carbon Budget: {args.budget}")

    print_section("Original Code", original_source)
    print_section("Optimized Code", optimized_source)

    # 7. Show optimization details
    if records:
        print("## Optimizations Applied\n")
        for i, rec in enumerate(records, 1):
            print(f"  {i}. [Line {rec.line}] {rec.description}")
            print(f"     Before: {rec.before}")
            print(f"     After : {rec.after}")
        print()
    else:
        print("No optimizations were applied — the code is already efficient.\n")

    # 8. Optionally write optimized code to file
    if args.output:
        generate_code_to_file(optimized_tree, args.output, language=language)
        print(f"Optimized code written to: {args.output}\n")

    # 9. Carbon audit
    if not args.no_audit:
        print("Starting carbon audit ...\n")
        report = run_audit(original_source, optimized_source, language=language)
        energy_reduction_pct, time_reduction_pct, final_score = calculate_combined_score(
            report.energy_before_kwh,
            report.energy_after_kwh,
            report.time_before_sec,
            report.time_after_sec,
        )
        rating = calculate_green_rating(final_score)
        print(f"Energy Before: {report.energy_before_kwh:.10f} kWh")
        print(f"Energy After: {report.energy_after_kwh:.10f} kWh")
        print(f"Energy Confidence: {report.energy_confidence.upper()}")
        print(f"Time Before: {report.time_before_sec:.10f} sec")
        print(f"Time After: {report.time_after_sec:.10f} sec")
        print(f"Time Confidence: {report.time_confidence.upper()}")
        print(f"CO2 Before: {report.co2_before_kgco2eq:.10f} kgCO2eq")
        print(f"CO2 After: {report.co2_after_kgco2eq:.10f} kgCO2eq")
        print(f"Energy Reduced: {energy_reduction_pct:.2f}%")
        print(f"Time Reduced: {time_reduction_pct:.2f}%")
        print(f"Final Score: {final_score:.2f}")
        print(f"Green Rating: {rating}")
        if args.budget is not None:
            limits = check_audit_limits(
                energy_after=report.energy_after_kwh,
                time_after=report.time_after_sec,
                co2_after=report.co2_after_kgco2eq,
                carbon_budget=args.budget,
            )
            print("Status: ✅ Within budget" if limits.get("carbon", False) else "Status: ❌ Carbon budget exceeded")
        print(report.format_report())
    else:
        print("Carbon audit skipped (--no-audit flag).\n")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "analyze":
        run_analyze(args)


if __name__ == "__main__":
    main()
