import re
import textwrap
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# =========================================================
# 1. SETTINGS
# =========================================================

# Keep this Python file in the same folder as your Excel file.
# The code will try these names automatically.
EXCEL_FILE_CANDIDATES = [
    "RQ2_data_used_to_draw_graphs_with_Approach_Type.xlsx",
    "RQ2_data_used_to_draw_graphs_with_Approach_Type(1).xlsx",
    "RQ2 data used to draw graphs with Approach Type.xlsx",
]

SHEET_OTHER = "use to plot other"
SHEET_INPUT = "use to plot input"
SHEET_OUTPUT = "use to plot output"

OUTPUT_DIR = Path("rq2_figures_selected")
OUTPUT_DIR.mkdir(exist_ok=True)

TOP_N = 25


# =========================================================
# 2. COLUMN NAMES
# =========================================================

TOOL_COL = "Tool / Method / Technique / Framework Name"
ACTIVITY_COL = "TDM Activity"
TD_TYPE_COL = "TD Type Addressed"
INPUT_COL = "Input Required"
OUTPUT_COL = "Output Produced"
AUTOMATION_COL = "Level of Automation"
APPROACH_TYPE_COL = "Approach Type"


# =========================================================
# 3. HELPER FUNCTIONS
# =========================================================

INVALID_LABELS = {
    "",
    "nan",
    "none",
    "null",
    "n/a",
    "na",
    "not applicable",
    "not specified",
    "not available",
    "no specific named tool/framework",
    "no specific named tool",
    "no named tool",
    "not counted as named tool",
}

SPLIT_PATTERN = r";"


def find_excel_file():
    """Find the Excel file in the current folder."""
    for file_name in EXCEL_FILE_CANDIDATES:
        path = Path(file_name)
        if path.exists():
            return path

    available_excels = sorted(Path(".").glob("*.xlsx"))

    if len(available_excels) == 1:
        return available_excels[0]

    raise FileNotFoundError(
        "Excel file not found. Put this Python file in the same folder as your Excel file.\n"
        "Expected one of these names:\n- "
        + "\n- ".join(EXCEL_FILE_CANDIDATES)
    )


def clean_column_names(df):
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def normalize_text_series(series):
    return (
        series
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )


def labels_from_series(series):
    """Return one clean label per row. Splits semicolon-separated cells if needed."""
    labels = (
        normalize_text_series(series.dropna())
        .str.split(SPLIT_PATTERN)
        .explode()
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    labels = labels[~labels.str.lower().isin(INVALID_LABELS)]

    return labels


def count_labels(df, column_name):
    if column_name not in df.columns:
        raise ValueError(f"Column not found: {column_name}")

    labels = labels_from_series(df[column_name])

    if labels.empty:
        return pd.Series(dtype=int)

    return labels.value_counts()


def wrap_labels(labels, width=35):
    return [
        "\n".join(textwrap.wrap(str(label), width=width))
        for label in labels
    ]


def require_columns(df, sheet_name, required_columns):
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(
            f"These columns are missing from sheet '{sheet_name}': "
            + ", ".join(missing)
        )


def save_bar_chart(counts, title, xlabel, filename, top_n=TOP_N):
    """Save a horizontal bar chart as PDF and PNG."""
    if counts.empty:
        print(f"Skipping {filename}: no data found.")
        return

    counts = counts[counts > 0]

    if counts.empty:
        print(f"Skipping {filename}: all values are zero.")
        return

    data = counts.head(top_n).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, max(5, 0.38 * len(data))))

    bars = ax.barh(wrap_labels(data.index, width=36), data.values)

    ax.set_xlabel(xlabel)
    ax.set_title(title)

    ax.bar_label(
        bars,
        labels=[str(int(value)) for value in data.values],
        padding=3,
        fontsize=8,
    )

    max_value = data.max()
    if max_value > 0:
        ax.set_xlim(0, max_value * 1.15)

    plt.tight_layout()

    pdf_path = OUTPUT_DIR / f"{filename}.pdf"
    png_path = OUTPUT_DIR / f"{filename}.png"

    plt.savefig(pdf_path, bbox_inches="tight")
    plt.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")


def save_vertical_bar_chart(counts, title, ylabel, filename):
    """Save a vertical bar chart as PDF and PNG."""
    if counts.empty:
        print(f"Skipping {filename}: no data found.")
        return

    counts = counts[counts > 0]

    if counts.empty:
        print(f"Skipping {filename}: all values are zero.")
        return

    data = counts.sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(8, 5))

    bars = ax.bar(wrap_labels(data.index, width=18), data.values)

    ax.set_ylabel(ylabel)
    ax.set_title(title)

    ax.bar_label(
        bars,
        labels=[str(int(value)) for value in data.values],
        padding=3,
        fontsize=9,
    )

    max_value = data.max()
    if max_value > 0:
        ax.set_ylim(0, max_value * 1.15)

    plt.tight_layout()

    pdf_path = OUTPUT_DIR / f"{filename}.pdf"
    png_path = OUTPUT_DIR / f"{filename}.png"

    plt.savefig(pdf_path, bbox_inches="tight")
    plt.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")


def reorder_automation_counts(counts):
    preferred_order = [
        "Manual",
        "Semi-automated",
        "Fully automated",
        "Other/Unclear",
    ]

    ordered = [label for label in preferred_order if label in counts.index]
    remaining = [label for label in counts.index if label not in preferred_order]

    return counts.reindex(ordered + remaining)


# =========================================================
# 4. LOAD DATA
# =========================================================

excel_file = find_excel_file()
print(f"Using Excel file: {excel_file}")
print("Loading data. This may take a little time...")

# Main sheet for automation, TD type, TDM activity, tools, methods/techniques.
df_other = pd.read_excel(
    excel_file,
    sheet_name=SHEET_OTHER,
    usecols=lambda c: str(c).strip() in {
        TOOL_COL,
        ACTIVITY_COL,
        TD_TYPE_COL,
        AUTOMATION_COL,
        APPROACH_TYPE_COL,
    },
    engine="openpyxl",
)
df_other = clean_column_names(df_other)

# Input sheet only for input required distribution.
df_input = pd.read_excel(
    excel_file,
    sheet_name=SHEET_INPUT,
    usecols=lambda c: str(c).strip() in {
        INPUT_COL,
    },
    engine="openpyxl",
)
df_input = clean_column_names(df_input)

# Output sheet only for output produced distribution.
df_output = pd.read_excel(
    excel_file,
    sheet_name=SHEET_OUTPUT,
    usecols=lambda c: str(c).strip() in {
        OUTPUT_COL,
    },
    engine="openpyxl",
)
df_output = clean_column_names(df_output)

print(f"Loaded '{SHEET_OTHER}' rows: {len(df_other)}")
print(f"Loaded '{SHEET_INPUT}' rows: {len(df_input)}")
print(f"Loaded '{SHEET_OUTPUT}' rows: {len(df_output)}")

require_columns(
    df_other,
    SHEET_OTHER,
    [
        TOOL_COL,
        ACTIVITY_COL,
        TD_TYPE_COL,
        AUTOMATION_COL,
        APPROACH_TYPE_COL,
    ],
)

require_columns(df_input, SHEET_INPUT, [INPUT_COL])
require_columns(df_output, SHEET_OUTPUT, [OUTPUT_COL])


# =========================================================
# 5. CREATE ONLY THE 7 REQUESTED GRAPHS
# =========================================================

# -------------------------
# Figure 1: Automation level distribution
# Sheet: use to plot other
# -------------------------

automation_counts = reorder_automation_counts(
    count_labels(df_other, AUTOMATION_COL)
)

save_vertical_bar_chart(
    automation_counts,
    title="Automation Level of Identified Approaches",
    ylabel="Number of paper-approach entries",
    filename="rq2_figure_1_automation_level_distribution",
)


# -------------------------
# Figure 2: Input required distribution
# Sheet: use to plot input
# -------------------------

input_counts = count_labels(df_input, INPUT_COL)

save_bar_chart(
    input_counts,
    title="Input Categories Required by TD Management Approaches",
    xlabel="Number of paper-approach-input entries",
    filename="rq2_figure_2_input_required_distribution",
    top_n=25,
)


# -------------------------
# Figure 3: Output produced distribution
# Sheet: use to plot output
# -------------------------

output_counts = count_labels(df_output, OUTPUT_COL)

save_bar_chart(
    output_counts,
    title="Output Categories Produced by TD Management Approaches",
    xlabel="Number of paper-approach-output entries",
    filename="rq2_figure_3_output_produced_distribution",
    top_n=25,
)


# -------------------------
# Figure 4: TD type distribution
# Sheet: use to plot other
# -------------------------

td_type_counts = count_labels(df_other, TD_TYPE_COL)

save_bar_chart(
    td_type_counts,
    title="Distribution of Technical Debt Types Addressed",
    xlabel="Number of paper-approach entries",
    filename="rq2_figure_4_td_type_distribution",
    top_n=25,
)


# -------------------------
# Figure 5: TDM activity distribution
# Sheet: use to plot other
# This replaces the previous heatmap.
# -------------------------

tdm_activity_counts = count_labels(df_other, ACTIVITY_COL)

save_bar_chart(
    tdm_activity_counts,
    title="Distribution of Technical Debt Management Activities",
    xlabel="Number of paper-approach entries",
    filename="rq2_figure_5_tdm_activity_distribution",
    top_n=25,
)


# -------------------------
# Figure 6: Tool distribution only
# Sheet: use to plot other
# Filter: Approach Type = Tool
# -------------------------

df_tools = df_other[
    normalize_text_series(df_other[APPROACH_TYPE_COL])
    .str.lower()
    .eq("tool")
].copy()

tool_counts = count_labels(df_tools, TOOL_COL)

save_bar_chart(
    tool_counts,
    title="Distribution of Tools Used for Technical Debt Management",
    xlabel="Number of paper-approach entries",
    filename="rq2_figure_6_tool_distribution",
    top_n=25,
)


# -------------------------
# Figure 7: Method/Technique distribution only
# Sheet: use to plot other
# Filter: Approach Type = Method/Technique
# -------------------------

df_methods = df_other[
    normalize_text_series(df_other[APPROACH_TYPE_COL])
    .str.lower()
    .eq("method/technique")
].copy()

method_counts = count_labels(df_methods, TOOL_COL)

save_bar_chart(
    method_counts,
    title="Distribution of Methods and Techniques Used for Technical Debt Management",
    xlabel="Number of paper-approach entries",
    filename="rq2_figure_7_method_technique_distribution",
    top_n=25,
)


# =========================================================
# 6. EXPORT SUMMARY COUNTS
# =========================================================

summary_file = OUTPUT_DIR / "rq2_selected_summary_counts.xlsx"

with pd.ExcelWriter(summary_file, engine="openpyxl") as writer:
    automation_counts.to_frame("Count").to_excel(
        writer,
        sheet_name="Automation Level",
    )

    input_counts.to_frame("Count").to_excel(
        writer,
        sheet_name="Input Required",
    )

    output_counts.to_frame("Count").to_excel(
        writer,
        sheet_name="Output Produced",
    )

    td_type_counts.to_frame("Count").to_excel(
        writer,
        sheet_name="TD Type",
    )

    tdm_activity_counts.to_frame("Count").to_excel(
        writer,
        sheet_name="TDM Activity",
    )

    tool_counts.to_frame("Count").to_excel(
        writer,
        sheet_name="Tools Only",
    )

    method_counts.to_frame("Count").to_excel(
        writer,
        sheet_name="Methods Techniques",
    )

print(f"\nSaved summary tables: {summary_file}")
print("All 7 requested RQ2 figures generated successfully.")