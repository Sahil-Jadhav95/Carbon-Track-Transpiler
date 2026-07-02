# Carbon-Track Transpiler (CTT)
<p align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-Web%20UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-Support-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![CodeCarbon](https://img.shields.io/badge/CodeCarbon-Carbon%20Audit-2E8B57?style=for-the-badge)
![Pytest](https://img.shields.io/badge/Pytest-Test%20Suite-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![CLI](https://img.shields.io/badge/CLI-Available-6C757D?style=for-the-badge&logo=windows-terminal&logoColor=white)

</p>
Carbon-Track Transpiler (CTT) is a Python-based source-to-source optimization tool that analyzes code, applies AST-based and JavaScript-aware transformations, and optionally measures the energy and carbon impact of the optimized result.

It includes both a Streamlit web interface and a command-line interface for optimizing Python and JavaScript programs.

## Features

- Automatic code validation before optimization
- Python AST-based optimization pipeline
- JavaScript source optimization
- Optional profiling to identify performance hotspots
- Carbon and energy estimation using CodeCarbon
- Optimized code generation
- Interactive Streamlit dashboard
- Before-and-after optimization reports

## Supported Languages

- Python
- JavaScript

## Project Structure
 
```text
CTT/
├── app.py
├── ctt/
│   ├── __main__.py
│   ├── cli.py
│   ├── parser.py
│   ├── optimizer.py
│   ├── optimizer_javascript.py
│   ├── code_generator.py
│   ├── carbon_audit.py
│   ├── profiler.py
│   ├── validator.py
│   ├── utils.py
│   ├── sample_code/
│   └── tests/
├── .gitignore
└── README.md
```

## Requirements

- Python 3.10 or later
- Virtual environment recommended

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Sahil-Jadhav95/Carbon-Track-Transpiler.git
cd Carbon-Track-Transpiler
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install streamlit altair pandas codecarbon escodegen esprima pytest
```

Install any additional packages required by the project modules if necessary.

## Usage

### Run the Streamlit application

```bash
streamlit run app.py
```

### Run the CLI

Show help:

```bash
python -m ctt
```

Analyze a Python file:

```bash
python -m ctt analyze path/to/file.py
```

Analyze a JavaScript file:

```bash
python -m ctt analyze path/to/file.js --language javascript
```

Save optimized output:

```bash
python -m ctt analyze path/to/file.py -o optimized_code.py
```

Disable carbon audit:

```bash
python -m ctt analyze path/to/file.py --no-audit
```

Enable profiling:

```bash
python -m ctt analyze path/to/file.py --profile
```

Select optimization mode:

```bash
python -m ctt analyze input.py --mode general
python -m ctt analyze input.py --mode energy
python -m ctt analyze input.py --mode both
```

Specify a carbon budget:

```bash
python -m ctt analyze input.py --budget 0.0001
```

## Workflow

```text
Input Source Code
        │
        ▼
Source Validation
        │
        ▼
      Parser
        │
        ▼
Optional Performance Profiling
        │
        ▼
Optimization Engine
        │
        ▼
Code Generator
        │
        ▼
Optional Carbon Audit
        │
        ▼
Optimized Source Code + Report
```

## Optimizations Performed

The optimization engine applies several compiler-inspired transformations, including:

- Constant folding
- Strength reduction
- Dead code elimination
- Redundant assignment removal
- Identity operation removal
- Boolean comparison simplification
- Variable inlining
- Common subexpression elimination
- Loop fusion
- Loop-to-comprehension conversion
- List-to-set membership conversion
- No-op loop removal

## Running Tests

```bash
pytest
```

## Carbon Audit

The project integrates CodeCarbon to estimate:

- Energy consumption
- CO2 emissions
- Carbon savings after optimization

Results depend on hardware configuration, execution environment, and workload characteristics.

## Notes

- Review generated code before deploying it in production.
- JavaScript optimization support may vary depending on the input program.
- Carbon audit results are approximate and intended for comparison purposes.

## License

This project is intended for academic and educational purposes.
