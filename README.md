# Carbon-Track Transpiler (CTT)

> **Carbon-Track Transpiler (CTT)** is a Python-based optimization tool that analyzes source code, applies AST-based and JavaScript-aware transformations, and optionally measures the carbon and energy impact of the optimized result.

It provides both a **Streamlit web interface** and a **Command Line Interface (CLI)**, enabling users to optimize Python and JavaScript programs while evaluating their environmental impact.

---

## 🚀 Features

* ✅ Automatic code validation before optimization
* 🌳 Python AST-based optimization pipeline
* 📜 JavaScript source optimization
* 📊 Optional profiling to identify performance hotspots
* 🌱 Carbon and energy usage estimation using CodeCarbon
* ⚡ Optimized code generation
* 📈 Interactive Streamlit dashboard
* 📋 Before-and-after optimization reports

---

## 🛠️ Supported Languages

* Python
* JavaScript

---

## 📁 Project Structure

```text
CTT/
│
├── app.py                          # Streamlit Web Application
├── documentation.md                # Technical Documentation
│
├── ctt/
│   ├── __main__.py                 # CLI Entry Point
│   ├── cli.py                      # Command-Line Interface
│   ├── parser.py                   # Source Parsing
│   ├── optimizer.py                # Python Optimizer
│   ├── optimizer_javascript.py     # JavaScript Optimizer
│   ├── code_generator.py           # Optimized Code Generator
│   ├── carbon_audit.py             # Carbon & Energy Measurement
│   ├── profiler.py                 # Performance Profiler
│   ├── validator.py                # Source Validator
│   ├── sample_code/                # Sample Programs
│   └── tests/                      # Test Cases
│
└── README.md
```

---

## 📋 Requirements

* Python **3.10** or later
* Virtual environment (recommended)

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/CTT.git
cd CTT
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install streamlit altair pandas codecarbon pytest
```

> Install any additional packages required by the project modules if necessary.

---

# ▶️ Usage

## Run the Streamlit Application

```bash
streamlit run app.py
```

---

## Run the Command-Line Interface

### Show Help

```bash
python -m ctt
```

### Analyze a Python File

```bash
python -m ctt analyze path/to/file.py
```

### Analyze a JavaScript File

```bash
python -m ctt analyze path/to/file.js --language javascript
```

### Save Optimized Output

```bash
python -m ctt analyze path/to/file.py -o optimized_code.py
```

### Disable Carbon Audit

```bash
python -m ctt analyze path/to/file.py --no-audit
```

### Enable Profiling

```bash
python -m ctt analyze path/to/file.py --profile
```

### Select Optimization Mode

General Optimization

```bash
python -m ctt analyze input.py --mode general
```

Energy Optimization

```bash
python -m ctt analyze input.py --mode energy
```

Combined Optimization

```bash
python -m ctt analyze input.py --mode both
```

### Specify a Carbon Budget

```bash
python -m ctt analyze input.py --budget 0.0001
```

---

# ⚙️ Workflow

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
(Optional) Performance Profiling
        │
        ▼
Optimization Engine
        │
        ▼
Code Generator
        │
        ▼
(Optional) Carbon Audit
        │
        ▼
Optimized Source Code + Report
```

---

# ✨ Optimizations Performed

The optimization engine applies several compiler-inspired transformations, including:

* Constant Folding
* Strength Reduction
* Dead Code Elimination
* Redundant Assignment Removal
* Identity Operation Removal
* Boolean Comparison Simplification
* Variable Inlining
* Common Subexpression Elimination
* Loop Fusion
* Loop-to-Comprehension Conversion
* List-to-Set Membership Conversion
* No-op Loop Removal

---

# 🧪 Running Tests

Execute the test suite using:

```bash
pytest
```

---

# 📊 Carbon Audit

The project integrates **CodeCarbon** to estimate:

* Energy Consumption
* CO₂ Emissions
* Carbon Savings after Optimization

> **Note:** Results depend on hardware configuration, execution environment, and workload characteristics.

---

# 📌 Notes

* Review generated code before deploying it in production.
* JavaScript optimization support may vary depending on the input program.
* Carbon audit results are approximate and intended for comparison purposes.

---

# 📄 License

This project is intended for academic and educational purposes.
