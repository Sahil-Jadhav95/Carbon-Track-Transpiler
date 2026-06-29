import ast
import sys
import os
import time
import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ctt.optimizer import optimize_ast
from ctt.optimizer_javascript import optimize_javascript_source
from ctt.code_generator import generate_code
from ctt.carbon_audit import (
    run_audit,
    AuditReport,
    check_carbon_budget,
    calculate_green_rating,
    calculate_combined_score,
    check_audit_limits,
)
from ctt.profiler import profile_code
from ctt.validator import validate_code_strict

# ---------------------------------------------------------------------------
# Page config & custom CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Carbon-Track Transpiler",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ---------- Global ---------- */
    .block-container { padding-top: 1.5rem; }

    /* ---------- Header ---------- */
    .ctt-header {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 2rem 2.5rem;
        border-radius: 14px;
        margin-bottom: 1.8rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,.25);
    }
    .ctt-header h1 {
        color: #4ade80;
        font-size: 2.4rem;
        margin: 0 0 .3rem 0;
        letter-spacing: 1px;
    }
    .ctt-header p {
        color: #94a3b8;
        font-size: 1.05rem;
        margin: 0;
    }

    /* ---------- Metric cards ---------- */
    .metric-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        flex: 1;
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        text-align: center;
    }
    .metric-card .label {
        color: #94a3b8;
        font-size: .82rem;
        text-transform: uppercase;
        letter-spacing: .8px;
        margin-bottom: .35rem;
    }
    .metric-card .value {
        font-size: 1.55rem;
        font-weight: 700;
    }
    .metric-card .value.green  { color: #4ade80; }
    .metric-card .value.blue   { color: #60a5fa; }
    .metric-card .value.amber  { color: #fbbf24; }
    .metric-card .value.red    { color: #f87171; }

    /* ---------- Optimization chips ---------- */
    .opt-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: .5rem .85rem;
        margin: .3rem .25rem;
        font-size: .85rem;
        color: #e2e8f0;
    }
    .opt-chip .line-badge {
        background: #4ade80;
        color: #0f172a;
        font-weight: 700;
        font-size: .72rem;
        padding: 2px 7px;
        border-radius: 5px;
    }

    /* ---------- Rule tags ---------- */
    .rule-tag {
        display: inline-block;
        background: linear-gradient(135deg, #4ade80 0%, #22d3ee 100%);
        color: #0f172a;
        font-weight: 600;
        font-size: .8rem;
        padding: 4px 12px;
        border-radius: 20px;
        margin: 4px 4px;
    }

    /* ---------- Section divider ---------- */
    .section-title {
        color: #4ade80;
        font-size: 1.15rem;
        font-weight: 600;
        border-left: 4px solid #4ade80;
        padding-left: .7rem;
        margin: 1.4rem 0 .8rem 0;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: #0f172a;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {
        color: #cbd5e1;
    }

    /* ---------- Footer ---------- */
    .ctt-footer {
        text-align: center;
        color: #475569;
        font-size: .78rem;
        margin-top: 2rem;
        padding: 1rem 0;
        border-top: 1px solid #1e293b;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="ctt-header">
    <h1>🌿 Carbon-Track Transpiler</h1>
    <p>Analyze Python/JavaScript code &bull; Detect inefficient patterns &bull; Generate optimized code &bull; Measure carbon impact</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — Rules & Info
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚡ Optimization Rules")
    st.markdown("""
    <div style="margin-top:.5rem">
        <span class="rule-tag">Constant Folding</span>
        <span class="rule-tag">Strength Reduction</span>
        <span class="rule-tag">Redundant Assignment</span>
        <span class="rule-tag">Identity Operations</span>
        <span class="rule-tag">Boolean Simplification</span>
        <span class="rule-tag">Dead Code Elimination</span>
        <span class="rule-tag">List→Set Membership</span>
        <span class="rule-tag">Loop→Comprehension</span>
        <br>
        <span class="rule-tag">Loop Fusion</span>
        <span class="rule-tag">No-op Loop Elimination</span>
        <span class="rule-tag">Variable Inlining</span>
        <span class="rule-tag">Subexpression Reuse</span>
        <span class="rule-tag">String Loop→join</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📖 How to use")
    st.markdown("""
1. Select source language
2. **Paste** code or **upload** a source file
3. Click **🚀 Analyze & Optimize**
4. View optimized code
5. Optionally run **Carbon Audit**
    """)

    st.markdown("---")
    st.markdown("### 🧠 Language")
    source_language = st.selectbox(
        "Source Language",
        ["python", "javascript"],
        index=0,
    )

    st.markdown("---")
    st.markdown("### 🔧 Settings")
    optimization_mode = st.radio(
        "Select Optimization Mode",
        ["both", "energy", "general"],
        index=0,
    )
    carbon_budget = st.number_input(
        "Set Carbon Budget (kgCO2eq)",
        min_value=0.0,
        value=0.0001,
        format="%.6f",
    )
    run_audit_flag = st.checkbox("Run Carbon Audit", value=False,
                                  help="Measure energy & CO₂ using CodeCarbon (takes extra time)")

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;color:#475569;font-size:.75rem;">
        Built with Python &bull; AST/JS transforms &bull; CodeCarbon &bull; Streamlit
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sample code loader
# ---------------------------------------------------------------------------

PYTHON_SAMPLE_CODE = '''\
# Sample: energy-inefficient Python code

width = 2 * 3
height = 10 + 5

def compute_square(x):
    return x ** 2

def compute_cube(x):
    return x ** 3

result = 0
result = 42

a = result * 1
b = result + 0
c = result ** 1

flag = True
if flag == True:
    print("Flag is on")
if flag == False:
    print("Flag is off")

def greet(name):
    return f"Hello, {name}"
    print("This will never run")

color = "red"
if color in ["red", "green", "blue"]:
    print("Primary color")

squares = []
for i in range(10):
    squares.append(i ** 2)

print("Width:", width)
print("Square of 5:", compute_square(5))
print("Result:", result)
'''

JAVASCRIPT_SAMPLE_CODE = '''\
// Sample: energy-inefficient JavaScript code

const width = 2 * 3;
const height = 10 + 5;

function computeSquare(x) {
    return x ** 2;
}

let result = 0;
let result2 = 42;

let a = result2 * 1;
let b = result2 + 0;

const flag = true;
if (flag === true) {
    console.log("Flag is on");
}

console.log("Width:", width);
console.log("Square of 5:", computeSquare(5));
'''

SAMPLE_CODE_BY_LANGUAGE = {
        "python": PYTHON_SAMPLE_CODE,
        "javascript": JAVASCRIPT_SAMPLE_CODE,
}


# ---------------------------------------------------------------------------
# Input area
# ---------------------------------------------------------------------------

st.markdown('<div class="section-title">📝 Input Code</div>', unsafe_allow_html=True)

input_tab1, input_tab2 = st.tabs(["✏️  Paste Code", "📂  Upload File"])

def _load_sample():
    """Callback: load sample code into the text area widget."""
    st.session_state["code_area"] = SAMPLE_CODE_BY_LANGUAGE[source_language]


def _validate_source(source_text: str, language: str) -> ast.AST | str:
    """Validate source text and return parseable structure for selected language."""
    is_valid, message = validate_code_strict(source_text, language=language)
    if not is_valid:
        st.error(message)
        st.stop()

    if language == "javascript":
        return source_text

    try:
        return ast.parse(source_text)
    except SyntaxError as e:
        error_msg = f"**Syntax Error** at line {e.lineno}, column {e.offset}"
        if e.msg:
            error_msg += f": {e.msg}"
        st.error(f"❌ {error_msg}")
        if e.text:
            st.code(e.text, language="python")
        st.stop()
    except Exception as e:
        st.error(f"❌ Parsing error: {str(e)}")
        st.stop()

with input_tab1:
    col_left, col_right = st.columns([5, 1])
    with col_right:
        st.button("Load Sample", use_container_width=True, on_click=_load_sample)
    source_code = st.text_area(
        "Paste your code here:",
        height=320,
        placeholder="Write or paste code here...",
        key="code_area",
        label_visibility="collapsed",
    )

with input_tab2:
    upload_types = ["py"] if source_language == "python" else ["js", "mjs", "cjs"]
    uploaded = st.file_uploader("Upload source file", type=upload_types)
    if uploaded is not None:
        source_code = uploaded.read().decode("utf-8")
        is_valid, message = validate_code_strict(source_code, language=source_language)
        if is_valid:
            st.success("✅ File validated successfully")
            st.code(source_code, language=source_language, line_numbers=True)

# ---------------------------------------------------------------------------
# Analyze button
# ---------------------------------------------------------------------------

analyze_clicked = st.button("🚀  Analyze & Optimize", type="primary", use_container_width=True)


# ---------------------------------------------------------------------------
# Core analysis logic
# ---------------------------------------------------------------------------

if analyze_clicked:
    if not source_code or not source_code.strip():
        st.warning("⚠️ Please write/upload source code first.")
        st.stop()

    tree = _validate_source(source_code, source_language)

    # --- Profile ---
    profile_start = time.perf_counter()
    hotspots = profile_code(source_code, language=source_language)
    profile_elapsed = time.perf_counter() - profile_start

    # --- Fixed loading delay + optimize ---
    with st.spinner("Analyzing and optimizing code ..."):
        time.sleep(3)
        if source_language == "python":
            optimized_tree, records = optimize_ast(tree, mode=optimization_mode, hotspots=hotspots)
            optimized_code = generate_code(optimized_tree, language="python")
        else:
            optimized_code, records = optimize_javascript_source(
                source_code,
                mode=optimization_mode,
                hotspots=hotspots,
            )

    # ---------------------------------------------------------------
    # Quick-stats row
    # ---------------------------------------------------------------
    total_opts = len(records)
    unique_rules = len({r.description.split(":")[0].strip() for r in records})
    lines_before = len(source_code.strip().splitlines())
    lines_after = len(optimized_code.strip().splitlines())

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="label">Optimizations Applied</div>
            <div class="value green">{total_opts}</div>
        </div>
        <div class="metric-card">
            <div class="label">Rules Triggered</div>
            <div class="value blue">{unique_rules}</div>
        </div>
        <div class="metric-card">
            <div class="label">Lines (Before)</div>
            <div class="value amber">{lines_before}</div>
        </div>
        <div class="metric-card">
            <div class="label">Lines (After)</div>
            <div class="value green">{lines_after}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------------
    # Side-by-side code comparison
    # ---------------------------------------------------------------
    st.markdown('<div class="section-title">🔄 Code Comparison</div>', unsafe_allow_html=True)

    col_orig, col_opt = st.columns(2)
    with col_orig:
        st.markdown("**Original Code**")
        st.code(source_code, language=source_language, line_numbers=True)
    with col_opt:
        st.markdown("**Optimized Code**")
        st.code(optimized_code, language=source_language, line_numbers=True)

    # ---------------------------------------------------------------
    # Optimizations detail
    # ---------------------------------------------------------------
    if records:
        st.markdown('<div class="section-title">🛠️ Optimizations Applied</div>', unsafe_allow_html=True)

        chips_html = ""
        for rec in records:
            chips_html += f"""
            <div class="opt-chip">
                <span class="line-badge">L{rec.line}</span>
                <span>{rec.description}</span>
            </div>
            """
        st.markdown(chips_html, unsafe_allow_html=True)

        # Detailed table
        with st.expander("📋 View detailed transformations", expanded=False):
            for i, rec in enumerate(records, 1):
                st.markdown(f"**{i}. [{rec.description}]** — Line {rec.line}")
                c1, c2 = st.columns(2)
                with c1:
                    st.code(rec.before, language=source_language)
                with c2:
                    st.code(rec.after, language=source_language)
    else:
        st.success("✅ No inefficiencies detected — your code is already optimized!")

    # ---------------------------------------------------------------
    # Profiling Results
    # ---------------------------------------------------------------
    st.markdown('<div class="section-title">⏱️ Profiling Results</div>', unsafe_allow_html=True)
    if hotspots:
        st.markdown("**Top Hotspots**")
        for hotspot in hotspots:
            st.markdown(f"- {hotspot['function']} ({hotspot['time']:.6f}s)")
    else:
        st.info("No hotspots detected")
    st.markdown(f"**Profiling Execution Time:** {profile_elapsed:.4f}s")

    # ---------------------------------------------------------------
    # Carbon Audit
    # ---------------------------------------------------------------
    if run_audit_flag:
        st.markdown('<div class="section-title">🌍 Carbon Audit Report</div>', unsafe_allow_html=True)

        with st.spinner("Running carbon audit — measuring energy for both code versions …"):
            report = run_audit(source_code, optimized_code, language=source_language)
            energy_reduction_pct, time_reduction_pct, final_score = calculate_combined_score(
                report.energy_before_kwh,
                report.energy_after_kwh,
                report.time_before_sec,
                report.time_after_sec,
            )
            rating = calculate_green_rating(final_score)

        st.markdown(f"**Optimization Mode:** {optimization_mode}")
        st.markdown(f"**Carbon Budget:** {carbon_budget:.10f} kgCO₂eq")

        # Metric cards for audit
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="label">Energy Before</div>
                <div class="value red">{report.energy_before_kwh:.10f} kWh</div>
            </div>
            <div class="metric-card">
                <div class="label">Energy After</div>
                <div class="value green">{report.energy_after_kwh:.10f} kWh</div>
            </div>
            <div class="metric-card">
                <div class="label">Energy Saved</div>
                <div class="value blue">{report.energy_reduction_kwh:.10f} kWh ({report.energy_reduction_pct:.2f}%)</div>
            </div>
        </div>
        <div class="metric-row">
            <div class="metric-card">
                <div class="label">CO₂ Before</div>
                <div class="value red">{report.co2_before_kgco2eq:.10f} kgCO₂eq</div>
            </div>
            <div class="metric-card">
                <div class="label">CO₂ After</div>
                <div class="value green">{report.co2_after_kgco2eq:.10f} kgCO₂eq</div>
            </div>
            <div class="metric-card">
                <div class="label">CO₂ Saved</div>
                <div class="value blue">{report.co2_reduction_kgco2eq:.10f} kgCO₂eq ({report.co2_reduction_pct:.2f}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Prepare energy data with floor for visibility
        energy_before_plot = report.energy_before_kwh if report.energy_before_kwh > 0 else 1e-12
        energy_after_plot = report.energy_after_kwh if report.energy_after_kwh > 0 else 1e-12
        energy_df = pd.DataFrame({
            "Metric": ["Before", "After"],
            "Energy (kWh)": [energy_before_plot, energy_after_plot],
        })
        
        # Prepare time data with floor for visibility
        time_before_ms = report.time_before_sec * 1000.0
        time_after_ms = report.time_after_sec * 1000.0
        time_floor_ms = 0.001
        # Keep bars visible for ultra-fast snippets; this only affects plotting, not reported values.
        plot_time_before_ms = time_before_ms if time_before_ms > 0 else time_floor_ms
        plot_time_after_ms = time_after_ms if time_after_ms > 0 else time_floor_ms
        time_df = pd.DataFrame({
            "Metric": ["Before", "After"],
            "Time (ms)": [plot_time_before_ms, plot_time_after_ms],
        })

        color_scale = alt.Scale(domain=["Before", "After"], range=["#f87171", "#4ade80"])
        energy_chart = (
            alt.Chart(energy_df)
            .mark_bar()
            .encode(
                x=alt.X("Metric:N", title=""),
                y=alt.Y("Energy (kWh):Q"),
                color=alt.Color("Metric:N", scale=color_scale, legend=None),
                tooltip=["Metric", alt.Tooltip("Energy (kWh):Q", format=".10f")],
            )
            .properties(height=260)
        )
        time_chart = (
            alt.Chart(time_df)
            .mark_bar()
            .encode(
                x=alt.X("Metric:N", title=""),
                y=alt.Y("Time (ms):Q"),
                color=alt.Color("Metric:N", scale=color_scale, legend=None),
                tooltip=["Metric", alt.Tooltip("Time (ms):Q", format=".6f")],
            )
            .properties(height=260)
        )

        st.subheader("Performance & Energy Comparison")
        chart_col1, chart_col2 = st.columns(2)
        
        # Check for visibility issues
        energy_visible = energy_before_plot > 1e-11 or energy_after_plot > 1e-11
        time_visible = plot_time_before_ms > 0.001 or plot_time_after_ms > 0.001
        
        with chart_col1:
            st.markdown("**Energy (kWh)**")
            st.altair_chart(energy_chart, use_container_width=True)
            if not energy_visible:
                st.caption("⚠️ Energy values are at noise floor (extremely small); using visualization floor for chart visibility.")
        with chart_col2:
            st.markdown("**Time (ms)**")
            st.altair_chart(time_chart, use_container_width=True)
            if time_before_ms <= 0 or time_after_ms <= 0:
                st.caption("⚠️ Time is extremely small for this snippet; a tiny plotting floor is used to keep bars visible.")
        
        st.caption("Measurements use a warmup run plus the median of 5 measured runs to reduce noise.")
        st.write(f"Energy Reduced: {energy_reduction_pct:.2f}% (Confidence: **{report.energy_confidence.upper()}**)")
        st.write(f"Time Reduced: {time_reduction_pct:.2f}% (Confidence: **{report.time_confidence.upper()}**)")
        st.write(f"Final Score: {final_score:.2f}")

        st.subheader("Green Code Rating")
        if rating.startswith("⭐⭐⭐ Excellent"):
            st.success(rating)
        elif rating.startswith("⭐⭐ Good"):
            st.info(rating)
        else:
            st.error(rating)

        progress_value = max(0, min(int((final_score / 40.0) * 100), 100))
        st.progress(progress_value)

        if check_carbon_budget(report.co2_after_kgco2eq, carbon_budget):
            st.success("Within carbon budget")
        else:
            st.error("Carbon budget exceeded")

        limits = check_audit_limits(
            energy_after=report.energy_after_kwh,
            time_after=report.time_after_sec,
            co2_after=report.co2_after_kgco2eq,
            carbon_budget=carbon_budget,
        )
    # ---------------------------------------------------------------
    # Download optimized code
    # ---------------------------------------------------------------
    st.markdown("---")
    st.download_button(
        label="⬇️  Download Optimized Code",
        data=optimized_code,
        file_name="optimized_code.py" if source_language == "python" else "optimized_code.js",
        mime="text/x-python" if source_language == "python" else "text/javascript",
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("""
<div class="ctt-footer">
    Carbon-Track Transpiler &copy; 2026 &bull; Built with AST &bull; CodeCarbon &bull; Streamlit
</div>
""", unsafe_allow_html=True)
