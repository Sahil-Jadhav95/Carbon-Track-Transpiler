# Carbon-Track Transpiler (CTT) - Comprehensive Technical Documentation

## Table of Contents
1. [Introduction and Philosophy](#1-introduction-and-philosophy)
    1. [The Environmental Impact of Computing](#11-the-environmental-impact-of-computing)
    2. [Core Objectives](#12-core-objectives)
    3. [Scope and Supported Languages](#13-scope-and-supported-languages)
2. [High-Level System Architecture](#2-high-level-system-architecture)
    1. [Data Flow Pipeline](#21-data-flow-pipeline)
    2. [Component Interactions](#22-component-interactions)
3. [Detailed Module Breakdown](#3-detailed-module-breakdown)
    1. [Frontend Interface (`app.py`)](#31-frontend-interface-apppy)
    2. [Command Line Interface (`cli.py`)](#32-command-line-interface-clipy)
    3. [Code Validator (`validator.py`)](#33-code-validator-validatorpy)
    4. [Code Profiler (`profiler.py`)](#34-code-profiler-profilerpy)
    5. [Python Optimizer Engine (`optimizer.py`)](#35-python-optimizer-engine-optimizerpy)
    6. [JavaScript Optimizer Engine (`optimizer_javascript.py`)](#36-javascript-optimizer-engine-optimizer_javascriptpy)
    7. [Code Generator (`code_generator.py`)](#37-code-generator-code_generatorpy)
    8. [Carbon Audit Engine (`carbon_audit.py`)](#38-carbon-audit-engine-carbon_auditpy)
4. [Deep Dive: Python Optimization Rules (AST Transformations)](#4-deep-dive-python-optimization-rules-ast-transformations)
    1. [Strength Reduction](#41-strength-reduction)
    2. [Constant Folding](#42-constant-folding)
    3. [Redundant Assignment Removal](#43-redundant-assignment-removal)
    4. [Identity Operation Removal](#44-identity-operation-removal)
    5. [Boolean Comparison Simplification](#45-boolean-comparison-simplification)
    6. [Dead Code Elimination](#46-dead-code-elimination)
    7. [List to Set Membership Conversion](#47-list-to-set-membership-conversion)
    8. [Loop-Append to List Comprehension](#48-loop-append-to-list-comprehension)
    9. [Loop Fusion](#49-loop-fusion)
    10. [No-op Loop Elimination](#410-no-op-loop-elimination)
    11. [Variable Inlining](#411-variable-inlining)
    12. [Common Subexpression Reuse](#412-common-subexpression-reuse)
5. [Deep Dive: JavaScript Optimization Rules](#5-deep-dive-javascript-optimization-rules)
6. [API Reference and Core Data Structures](#6-api-reference-and-core-data-structures)
    1. [OptimizationRecord](#61-optimizationrecord)
    2. [AuditReport](#62-auditreport)
    3. [Hotspot Definition](#63-hotspot-definition)
7. [Carbon Auditing Methodology](#7-carbon-auditing-methodology)
    1. [The CodeCarbon Integration](#71-the-codecarbon-integration)
    2. [Measurement Precision and Noise Filtering](#72-measurement-precision-and-noise-filtering)
    3. [Green Code Rating System](#73-green-code-rating-system)
8. [Installation and Environment Setup](#8-installation-and-environment-setup)
    1. [Prerequisites](#81-prerequisites)
    2. [Virtual Environment Setup](#82-virtual-environment-setup)
    3. [Dependency Management](#83-dependency-management)
9. [Usage Guide](#9-usage-guide)
    1. [Streamlit GUI Usage](#91-streamlit-gui-usage)
    2. [CLI Usage and Flags](#92-cli-usage-and-flags)
10. [Performance Characteristics and Limitations](#10-performance-characteristics-and-limitations)
11. [Security Considerations](#11-security-considerations)
12. [Future Enhancements and Roadmap](#12-future-enhancements-and-roadmap)

---

## 1. Introduction and Philosophy

### 1.1 The Environmental Impact of Computing
The rapid expansion of software applications, cloud computing, and massive data centers has led to an unprecedented increase in global electricity consumption. Every CPU cycle, memory allocation, and disk read operation draws power. While hardware engineers continue to improve processor efficiency, software engineers often prioritize development speed over computational efficiency, leading to "bloated" code. The Carbon-Track Transpiler (CTT) bridges this gap by automatically refactoring code into its most mathematically and structurally efficient form, thereby saving energy.

### 1.2 Core Objectives
- **Code Optimization**: Automatically identify and refactor inefficient coding patterns into optimal ones without altering the semantic meaning or output of the program.
- **Energy Measurement**: Measure the exact energy consumption (in kWh) and carbon emissions (in kgCO2eq) of code execution using hardware-level metrics via external libraries.
- **Developer Education**: Provide developers with actionable insights, side-by-side comparisons, and explanations of why certain patterns are inefficient.
- **Metrics Visibility**: Provide clear, undeniable empirical proof of energy savings.

### 1.3 Scope and Supported Languages
CTT primarily targets Python because of its vast popularity in data science and web development—domains notorious for high compute costs. Python's dynamic nature makes standard compilation optimizations difficult, making source-to-source transpilation via Abstract Syntax Trees (AST) highly valuable. Secondary support is provided for JavaScript to cater to frontend and Node.js backend developers.

---

## 2. High-Level System Architecture

The CTT system is architected as a modular, linear pipeline. Data flows from the input source through validation, profiling, and optimization, ending in code generation and optional carbon auditing.

### 2.1 Data Flow Pipeline

1. **Input Layer**: Code is ingested either through the Streamlit Web App (`app.py`) via text area/file upload, or through the CLI (`cli.py`) via file reading.
2. **Validation (`validator.py`)**: The raw string is parsed. For Python, `ast.parse()` is used to catch `SyntaxError`s immediately. A strict mode enforces safety constraints.
3. **Profiling (`profiler.py`)**: Before optimization, the code is analyzed to find "hotspots" (frequently executed or time-consuming functions). This directs the optimizer to focus heavily on performance-critical sections to balance the transpilation overhead.
4. **AST Generation**: The source code string is converted into an Abstract Syntax Tree (using Python's native `ast` module).
5. **Optimization Engine (`optimizer.py`)**: Applies a series of `ast.NodeTransformer` passes over the AST. Each transformer looks for specific sub-optimal patterns and safely mutates the AST into a more efficient form.
6. **Code Generation (`code_generator.py`)**: The mutated AST is unparsed back into a standard Python source code string.
7. **Carbon Auditing (`carbon_audit.py`)**: If requested, this module isolates both the original and optimized code in secure subprocesses, running them repeatedly while tracking hardware energy metrics.
8. **Presentation Layer**: Results, including the modified code, optimization logs, and charts, are returned to the user via the CLI output or the Streamlit interactive GUI.

### 2.2 Component Interactions
The orchestrator (either `app.py` or `cli.py`) handles the state passing. It holds the string representation of the code, passes it to the `optimizer` which returns the `ast.Module` and a list of `OptimizationRecord` objects. The `code_generator` consumes the `ast.Module` and returns a string. The `carbon_audit` consumes both strings and returns an `AuditReport` dataclass.

---

## 3. Detailed Module Breakdown

### 3.1 Frontend Interface (`app.py`)
Built using Streamlit, this serves as the primary graphical interface.
- **Visual Design**: Implements custom CSS injection for a dark-mode, neon-accented aesthetic (Green/Blue/Amber) to provide a premium feel. Features responsive metric cards.
- **Features**: Interactive code editors, dual tabs for pasting vs. uploading, and side-by-side diff viewers.
- **Visualizations**: Integrates Altair and Pandas to render interactive bar charts comparing Execution Time (ms), Energy (kWh), and Carbon Emissions (kgCO2eq) before and after optimization.
- **State Management**: Manages session state for sample code loading and user configurations.

### 3.2 Command Line Interface (`cli.py`)
Designed for integration into CI/CD pipelines, Git hooks, or batch processing.
- Uses Python's `argparse` to handle standard GNU-style arguments.
- Supports processing whole directories.
- Provides clean, colorized terminal output indicating exactly which rules were applied and at which line numbers.
- Handles exit codes appropriately (e.g., exiting with `1` if validation fails).

### 3.3 Code Validator (`validator.py`)
Ensures that the input is safe and structurally sound before the transpiler attempts to modify it.
- Uses `ast.parse()` to catch `SyntaxError` early.
- Implements `validate_code_strict()` which walks the AST looking for dangerous or dynamic constructs such as `eval()`, `exec()`, or complex metaprogramming that the static optimizer cannot safely handle without risking behavioral changes.

### 3.4 Code Profiler (`profiler.py`)
Identifies hotspots to ensure that optimization overhead is justified by runtime performance gains.
- Implements rudimentary tracing or AST complexity analysis to flag critical functions (e.g., functions containing nested loops, heavy mathematical operations).
- The Optimizer can utilize this hotspot list via the `_HotspotScopedTransformer` class to restrict aggressive, time-consuming transformations only to code paths that matter.

### 3.5 Python Optimizer Engine (`optimizer.py`)
The absolute core of the project. It extends `ast.NodeTransformer` for over a dozen distinct rules.
- Safely mutates the abstract syntax tree in memory.
- Maintains an `OptimizationRecord` for every single mutation applied, ensuring full transparency. If a transformation might change the semantics of the code (e.g., floating-point precision loss), it requires strict validation.
- Traverses the AST bottom-up in some cases and top-down in others, depending on the rule requirements.

### 3.6 JavaScript Optimizer Engine (`optimizer_javascript.py`)
A parallel engine for JavaScript code.
- Because Python's `ast` module cannot parse JS, this module utilizes external tools or advanced regex string manipulation to apply rules.
- Implements JS-specific optimizations such as converting `var` to `let`/`const`, simplifying strict equality checks, and loop optimizations tailored for the V8 engine.

### 3.7 Code Generator (`code_generator.py`)
Converts the optimized AST back into raw source code.
- Wraps `ast.unparse()` for Python >= 3.9.
- Ensures correct indentation, formatting, and preserves docstrings where possible.

### 3.8 Carbon Audit Engine (`carbon_audit.py`)
Responsible for the empirical measurement of efficiency gains.
- **Tooling**: Leverages `codecarbon.OfflineEmissionsTracker`.
- **Methodology**: 
  1. Runs a "warm-up" execution to cache imports and prevent cold-start penalties from skewing data.
  2. Executes the original code $N$ times (default 5) in a sandboxed subprocess.
  3. Executes the optimized code $N$ times.
  4. Collects hardware-level energy usage (CPU + RAM) and calculates the median.
- **Metrics**: Calculates percentage reduction, confidence scores, and verifies if the optimization stays within a user-defined "Carbon Budget".

---

## 4. Deep Dive: Python Optimization Rules (AST Transformations)

The `optimizer.py` module applies a sequential pipeline of AST transformers. Understanding these rules is crucial to understanding how CTT saves energy.

### 4.1 Strength Reduction
Replaces computationally expensive operations with cheaper, mathematically equivalent operations.
- **Target**: Exponentiation (`**`) by small, constant integers.
- **Mechanics**: Intercepts `ast.BinOp` where the operator is `ast.Pow`. If the right operand is an `ast.Constant` between 2 and 4, it rewrites the tree into nested `ast.Mult` nodes.
- **Example Before**: 
  ```python
  area = radius ** 2
  volume = size ** 3
  ```
- **Example After**: 
  ```python
  area = radius * radius
  volume = size * size * size
  ```
- **Energy Impact**: Multiplication is implemented directly in the ALU hardware and requires 1-3 clock cycles, whereas `pow()` involves complex floating-point algorithms taking significantly more cycles.

### 4.2 Constant Folding
Evaluates expressions involving constant literals at transpile-time rather than runtime.
- **Target**: Binary and Unary operations on constants (`ast.Constant`).
- **Mechanics**: Intercepts `ast.BinOp` and `ast.UnaryOp`. If both sides are constants and the operator is safe (e.g., `+`, `-`, `*`, `//`), the transpiler evaluates the result in Python and replaces the entire subtree with a single `ast.Constant`.
- **Example Before**: 
  ```python
  SECONDS_IN_DAY = 60 * 60 * 24
  inverse = -(-5)
  ```
- **Example After**: 
  ```python
  SECONDS_IN_DAY = 86400
  inverse = 5
  ```
- **Energy Impact**: Prevents the runtime interpreter from repeatedly calculating static values, especially inside loops.

### 4.3 Redundant Assignment Removal
Detects and removes variables that are immediately reassigned before being read.
- **Target**: Consecutive assignments to the exact same variable name.
- **Mechanics**: Scans block bodies (lists of `ast.stmt`). If `body[i]` and `body[i+1]` are both `ast.Assign` to the same `ast.Name`, and the first assignment has no side effects, it removes `body[i]`.
- **Example Before**:
  ```python
  result = 0
  result = calculate_complex_value()
  ```
- **Example After**:
  ```python
  result = calculate_complex_value()
  ```
- **Energy Impact**: Saves memory allocation overhead, garbage collection pressure, and dictionary lookups in the local namespace.

### 4.4 Identity Operation Removal
Removes operations that mathematically have no effect on the value.
- **Target**: Addition by 0, multiplication by 1, division by 1, power of 1.
- **Mechanics**: Examines `ast.BinOp`. Checks for specific operator-operand pairs like `ast.Mult` and `1`.
- **Example Before**: 
  ```python
  adjusted_width = base_width * 1 + 0
  ```
- **Example After**: 
  ```python
  adjusted_width = base_width
  ```
- **Energy Impact**: Eliminates unnecessary bytecode instructions (e.g., `BINARY_MULTIPLY`, `BINARY_ADD`) entirely from the execution path.

### 4.5 Boolean Comparison Simplification
Simplifies verbose boolean checks.
- **Target**: Comparing booleans against `True` or `False` using `==` or `!=`.
- **Mechanics**: Intercepts `ast.Compare`. Looks for `ast.Eq` or `ast.NotEq` where the comparator is an `ast.Constant(value=True)` or `ast.Constant(value=False)`.
- **Example Before**: 
  ```python
  if is_ready == True:
      start()
  if is_finished == False:
      wait()
  ```
- **Example After**: 
  ```python
  if is_ready:
      start()
  if not is_finished:
      wait()
  ```
- **Energy Impact**: Direct truthiness evaluation in Python is significantly faster at the C level than invoking the `__eq__` magic method or comparing object identities.

### 4.6 Dead Code Elimination
Removes code that mathematically cannot be executed.
- **Target**: Statements following unconditional control flow terminators (`return`, `break`, `continue`).
- **Mechanics**: Iterates over statements in a block. If an `ast.Return`, `ast.Break`, or `ast.Continue` is found, all subsequent statements in that block are truncated.
- **Example Before**:
  ```python
  def fetch_data():
      return db.query()
      print("Query complete") # Unreachable
      db.close() # Unreachable
  ```
- **Example After**:
  ```python
  def fetch_data():
      return db.query()
  ```
- **Energy Impact**: Reduces the size of the compiled `.pyc` bytecode, resulting in faster parsing times, faster module loading, and slightly smaller memory footprints.

### 4.7 List to Set Membership Conversion
Converts list literals used in `in` membership checks into sets.
- **Target**: `x in [...]` or `x not in [...]` where the list contains only constants.
- **Mechanics**: Intercepts `ast.Compare`. If the operator is `ast.In` and the right side is an `ast.List` of constants, it converts the `ast.List` to an `ast.Set`.
- **Example Before**: 
  ```python
  if file_extension in [".jpg", ".png", ".gif", ".webp"]:
      process_image()
  ```
- **Example After**: 
  ```python
  if file_extension in {".jpg", ".png", ".gif", ".webp"}:
      process_image()
  ```
- **Energy Impact**: A list lookup operates in $O(N)$ time complexity, requiring a linear scan of elements. A set lookup uses a hash table and operates in $O(1)$ constant time. Inside a loop, this transforms an $O(M \times N)$ operation into an $O(M)$ operation, yielding massive CPU savings.

### 4.8 Loop-Append to List Comprehension
Translates a basic `for` loop that appends to a list into a highly optimized native list comprehension.
- **Target**: Pattern matching an empty list assignment followed by a for-loop with a single `append()` method call.
- **Mechanics**: Scans blocks for an `ast.Assign` of `[]`, followed by an `ast.For`. It extracts the iteration target, the iterable, and the appended value to construct an `ast.ListComp`.
- **Example Before**:
  ```python
  squares = []
  for i in range(1000):
      squares.append(i * i)
  ```
- **Example After**:
  ```python
  squares = [i * i for i in range(1000)]
  ```
- **Energy Impact**: List comprehensions are implemented entirely in optimized C-code within CPython. They avoid the tremendous overhead of repeatedly executing Python bytecode to look up the `append` method attribute, load arguments, and invoke the function frame on every iteration.

### 4.9 Loop Fusion
Merges consecutive loops that iterate over the exact same sequence.
- **Target**: Two adjacent `for` loops with identical targets and iterators, lacking complex control flow.
- **Mechanics**: Analyzes pairs of `ast.For` nodes. Checks `ast.dump(first.iter) == ast.dump(second.iter)`. Verifies no `break`, `continue`, or `return` exists in either body. Fuses the `body` lists.
- **Example Before**:
  ```python
  for item in data:
      process_a(item)
  for item in data:
      process_b(item)
  ```
- **Example After**:
  ```python
  for item in data:
      process_a(item)
      process_b(item)
  ```
- **Energy Impact**: Reduces the iteration overhead by exactly half. The Python interpreter only needs to invoke the iterator's `__next__()` method and bind the variable once per element, instead of twice.

### 4.10 No-op Loop Elimination
Removes loops that do absolutely nothing.
- **Target**: Loops where the body consists solely of `ast.Pass` nodes.
- **Mechanics**: Filters out `ast.For` nodes where `all(isinstance(stmt, ast.Pass) for stmt in node.body)`.
- **Example Before**:
  ```python
  for _ in range(1000000):
      pass
  ```
- **Example After**: `(Removed entirely)`
- **Energy Impact**: Completely bypasses the CPU overhead of executing millions of empty iterations.

### 4.11 Variable Inlining
Inlines variables that are assigned and immediately returned.
- **Target**: `ast.Assign` immediately followed by an `ast.Return` of that same variable.
- **Mechanics**: Checks if `body[i]` targets name X, and `body[i+1]` returns name X. Replaces both with a direct return of the assigned value.
- **Example Before**:
  ```python
  def get_data():
      result = query_database()
      return result
  ```
- **Example After**:
  ```python
  def get_data():
      return query_database()
  ```
- **Energy Impact**: Skips the memory allocation and namespace dictionary update required to store the temporary variable.

### 4.12 Common Subexpression Reuse
Detects identical consecutive assignments and reuses the variable.
- **Target**: Consecutive identical right-hand side expressions.
- **Example Before**:
  ```python
  x = a + b * c
  y = a + b * c
  ```
- **Example After**:
  ```python
  x = a + b * c
  y = x
  ```
- **Energy Impact**: Reduces duplicate computation.

---

## 5. Deep Dive: JavaScript Optimization Rules

While Python is the primary target, CTT includes a parallel module (`optimizer_javascript.py`) to handle JavaScript files. Because Python's standard `ast` module cannot parse JavaScript, this module relies on distinct methodologies.

### JS Methodology
- **Regex and String Manipulation**: Fast, pattern-based replacements for well-known JS inefficiencies.
- **AST Delegation**: Optionally calling out to a Node.js process running a Babel-based script to parse, mutate, and generate JS.

### Applicable JS Rules
1. **Var to Let/Const**: Modernizing variable declarations.
2. **Strict Equality**: Converting `==` to `===` where type coercion is unnecessary, saving engine type-checking overhead.
3. **Loop Enhancements**: Replacing traditional `for(let i=0; i<arr.length; i++)` loops with `for...of` or `.forEach` where appropriate.
4. **Math Optimizations**: Similar constant folding and strength reduction (e.g., replacing `Math.pow(x, 2)` with `x * x`).

---

## 6. API Reference and Core Data Structures

### 6.1 `OptimizationRecord`
Used to track what the transpiler changed. It is essential for the UI and CLI reporting.
```python
class OptimizationRecord:
    def __init__(self, line: int, description: str, before: str, after: str):
        self.line = line              # Line number in the original code
        self.description = description# Human-readable rule description
        self.before = before          # Code snippet prior to mutation
        self.after = after            # Code snippet post-mutation

    def __repr__(self):
        return f"Line {self.line}: {self.description}"
```

### 6.2 `AuditReport`
Encapsulates the empirical carbon footprint and performance metrics gathered during the execution runs.
```python
@dataclass
class AuditReport:
    energy_before_kwh: float = 0.0      # Total energy used by original code
    energy_after_kwh: float = 0.0       # Total energy used by optimized code
    co2_before_kgco2eq: float = 0.0     # Carbon footprint before
    co2_after_kgco2eq: float = 0.0      # Carbon footprint after
    time_before_sec: float = 0.0        # Execution time before
    time_after_sec: float = 0.0         # Execution time after
    energy_confidence: str = "unknown"  # Statistical confidence ('high', 'medium', 'low')
    time_confidence: str = "unknown"
```
**Dynamic Properties**:
The class contains calculated properties that the Streamlit GUI utilizes directly:
- `energy_reduction_kwh`: Absolute kWh saved.
- `energy_reduction_pct`: Percentage of energy saved.
- `time_reduction_sec`: Absolute seconds saved.
- `co2_reduction_pct`: Percentage reduction in carbon footprint.

### 6.3 Hotspot Definition
The profiler generates a list of dictionaries representing hotspots:
```python
Hotspot = {
    "function": "calculate_matrix", # Name of the function
    "time": 0.45,                   # Execution time in seconds
    "calls": 1000                   # Number of times invoked
}
```

---

## 7. Carbon Auditing Methodology

The `carbon_audit.py` module is what elevates CTT from a simple linter to a scientific energy measurement tool.

### 7.1 The CodeCarbon Integration
CTT uses the open-source `codecarbon` library. Specifically, it uses the `OfflineEmissionsTracker` class to operate without requiring an external internet connection to an API. CodeCarbon interfaces directly with hardware-level metrics APIs (like Intel RAPL on Linux or PowerGadget on Mac/Windows) to measure the exact watt-hours drawn by the CPU and RAM during the execution window.

### 7.2 Measurement Precision and Noise Filtering
Measuring energy for micro-scripts is notoriously difficult due to OS background tasks. CTT solves this by:
1. **Subprocess Isolation**: Executing code in an isolated environment via `subprocess.run()`.
2. **Warm-up Cycles**: The script is executed once without tracking to ensure Python caches the compiled `.pyc` and standard libraries.
3. **Multi-run Median**: The code is executed `_DEFAULT_RUNS` (usually 5) times. The median value of energy and time is taken, heavily mitigating the impact of random OS context-switches or background spikes.
4. **Coefficient of Variation**: Confidence is calculated. If the variance between the 5 runs is $<5\%$, confidence is HIGH. If $>15\%$, confidence is LOW.

### 7.3 Green Code Rating System
A combined score is calculated using a weighted formula:
`Score = (0.6 * Energy Reduction %) + (0.4 * Time Reduction %)`

This score translates to a user-friendly rating:
- **⭐⭐⭐ Excellent** (Score $\ge$ 40)
- **⭐⭐ Good** (Score $\ge$ 15)
- **⭐ Poor** (Score < 15)

---

## 8. Installation and Environment Setup

### 8.1 Prerequisites
- **Python**: Version 3.10 or strictly higher is required due to modern `ast` features (like `ast.unparse`).
- **Node.js**: Version 14+ is required if utilizing the JavaScript transpilation features.
- **OS**: Works on Linux, Windows, and macOS. However, hardware-level energy tracking (CodeCarbon) is most accurate on Linux via Intel RAPL.

### 8.2 Virtual Environment Setup
It is highly recommended to run CTT in an isolated environment.
```bash
git clone <repository_url>
cd CTT
python -m venv .venv
```
**Activate the environment:**
- Windows: `.venv\Scripts\activate`
- macOS/Linux: `source .venv/bin/activate`

### 8.3 Dependency Management
Install the necessary packages via pip:
```bash
pip install streamlit codecarbon altair pandas
```

---

## 9. Usage Guide

### 9.1 Streamlit GUI Usage
The graphical interface is the best way to visualize the changes.
```bash
streamlit run app.py
```
This spawns a local web server at `http://localhost:8501`.
1. **Sidebar Config**: Select the target language and toggle the Optimization Modes (Energy, General, Both). Set your desired Carbon Budget threshold.
2. **Input**: Use the tabs to either paste raw code into the text area or upload a `.py`/`.js` file.
3. **Execution**: Click **Analyze & Optimize**.
4. **Review Results**:
   - The top row displays quick metrics (Optimizations Applied, Rules Triggered, Lines saved).
   - A side-by-side code diff clearly shows the before-and-after.
   - The **Carbon Audit Report** displays bar charts comparing the exact kWh and ms timings.
5. **Export**: Click the **Download Optimized Code** button.

### 9.2 CLI Usage and Flags
For automated or headless usage in backend servers or CI/CD pipelines.
```bash
python -m ctt.cli --input path/to/script.py --output path/to/optimized.py --audit
```
**Core Flags**:
- `-i`, `--input`: Path to the input file (Required).
- `-o`, `--output`: Path to save the optimized file. If omitted, it prints to `stdout`.
- `-l`, `--language`: `python` or `javascript` (Defaults to `python`).
- `--audit`: Boolean flag. If present, runs the CodeCarbon subprocess measurements.
- `--budget`: Set a float value for the max kgCO2eq allowed. Exits with error code if exceeded.

---

## 10. Performance Characteristics and Limitations

### Strengths
- **Static Safety**: AST transformations are mathematically much safer than regex-based text replacements. They understand scoping, nesting, and syntax boundaries.
- **Empirical Measurability**: The integration of CodeCarbon provides hard proof of energy savings, bringing empirical science into the art of code optimization.

### Known Limitations
- **Dynamic Typing Ambiguity**: Python's dynamic nature means it's often impossible for a static analyzer to determine variable types definitively. For example, `a + b` might be numeric addition, or it might be string concatenation. CTT must act conservatively; if it cannot guarantee safety, it skips the optimization.
- **Audit Execution Overhead**: Running the full Carbon Audit involves multiple sandboxed subprocess executions. This can take anywhere from 5 to 15 seconds depending on the complexity of the script and the number of runs.
- **JavaScript Support Constraints**: JS support relies heavily on external runtime environments (Node) rather than native Python AST integrations, making it slightly slower and harder to maintain cross-platform.

---

## 11. Security Considerations

When building transpilers, security is a major concern, particularly when evaluating expressions or executing audits.
- **Sandboxed Execution**: The `carbon_audit.py` module executes the target code within an `exec()` call restricted by a custom `SAFE_BUILTINS` dictionary. Access to dangerous modules (`os`, `sys`, `subprocess`) is severely restricted during the audit phase.
- **Timeout Restrictions**: Subprocesses are given a strict timeout (e.g., 120 seconds). If an optimization accidentally induces an infinite loop, the subprocess is killed gracefully without taking down the main CTT application.
- **Validator Checks**: The `validator.py` ensures that malicious payloads (like obscure eval chains) are rejected before reaching the AST transformer.

---

## 12. Future Enhancements and Roadmap

1. **Type Hint Integration (PEP 484)**: Modifying the `optimizer.py` to respect and utilize Python type hints (`: int`, `: list`). If the transpiler knows an operation involves strictly integers, it can safely apply much more aggressive math optimizations.
2. **Machine Learning Hotspot Prediction**: Training a lightweight neural network to predict which functions will become execution hotspots purely from static code metrics, entirely bypassing the need for a dynamic profiler.
3. **CI/CD Integration Hooks**: Developing official GitHub Actions and GitLab CI plugins that automatically comment on Pull Requests with the projected energy savings of the merged code.
4. **Wider Language Parsing**: Integrating native parsers for compiled languages like Go, Java, and Ruby.
5. **Advanced Loop Unrolling**: Automatically unrolling small loops (e.g., `for i in range(3)`) into sequential statements to maximize CPU instruction pipelining and cache hits.
