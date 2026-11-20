import os
import re
import pandas as pd
import matplotlib.pyplot as plt


# =========================
# CONFIGURATION
# =========================

EXCEL_FILE = "output/RQ3_cleaned_and_analysis.xlsx"
DATA_SHEET = "Cleaned_Data"
OUTPUT_DIR = "RQ3_figures"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# BASIC SETTINGS
# =========================

INVALID_VALUES = {
    "",
    "NR",
    "NA",
    "N/A",
    "NONE",
    "NULL",
    "NAN",
    "NOT REPORTED",
    "NOT APPLICABLE",
    "UNCLEAR",
    "PDF NOT FOUND",
    "NO TEXT EXTRACTED",
}


def clean_text(value):
    """Clean cell text."""
    if pd.isna(value):
        return ""
    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)
    return value


def is_valid_value(value):
    """Return False for NR, NA, empty, PDF not found, etc."""
    value = clean_text(value)
    if value.upper() in INVALID_VALUES:
        return False
    if "PDF not found" in value:
        return False
    if "No text extracted" in value:
        return False
    return True


def split_multivalue(value):
    """
    Split semicolon-separated values.
    Example: 'Machine learning; NLP; Text mining'
    """
    value = clean_text(value)
    if not is_valid_value(value):
        return []

    parts = re.split(r";|\|", value)
    cleaned = []

    for part in parts:
        part = clean_text(part)
        if is_valid_value(part):
            cleaned.append(part)

    return cleaned


def find_column(df, possible_names):
    """
    Find a column even if the exact name slightly differs.
    """
    normalized = {col.strip().lower(): col for col in df.columns}

    for name in possible_names:
        key = name.strip().lower()
        if key in normalized:
            return normalized[key]

    return None


def remove_failed_rows(df):
    """Remove rows where extraction failed."""
    failed_pattern = r"PDF not found|No text extracted"

    mask = df.astype(str).apply(
        lambda row: row.str.contains(failed_pattern, case=False, regex=True).any(),
        axis=1
    )

    return df[~mask].copy()


# =========================
# LOAD DATA
# =========================

try:
    df = pd.read_excel(EXCEL_FILE, sheet_name=DATA_SHEET)
except ValueError:
    print(f"[WARN] Sheet '{DATA_SHEET}' not found. Reading first sheet instead.")
    df = pd.read_excel(EXCEL_FILE)

df.columns = df.columns.astype(str).str.strip()
df = remove_failed_rows(df)

print(f"[INFO] Loaded usable rows: {len(df)}")
print(f"[INFO] Columns found: {list(df.columns)}")


# =========================
# FREQUENCY HELPERS
# =========================

def count_single_column(df, column_name):
    """Count values from a single-value column."""
    values = []

    for value in df[column_name]:
        value = clean_text(value)
        if is_valid_value(value):
            values.append(value)

    return pd.Series(values).value_counts()


def count_multivalue_column(df, column_name):
    """Count values from a semicolon-separated multi-value column."""
    values = []

    for value in df[column_name]:
        values.extend(split_multivalue(value))

    return pd.Series(values).value_counts()


def make_metric_categories(row):
    """
    Fallback metric categorization if your Excel does not already have
    a Metric_Category column.
    """
    categories = set()

    td_metrics = clean_text(row.get("TD_Metrics", ""))
    software_metrics = clean_text(row.get("Software_Metrics", ""))
    ai_metrics = clean_text(row.get("AI_Performance_Metrics", ""))

    combined_td = td_metrics.lower()
    combined_sw = software_metrics.lower()
    combined_ai = ai_metrics.lower()

    if is_valid_value(td_metrics):
        if any(k in combined_td for k in [
            "principal", "interest", "remediation", "cost", "effort",
            "time", "td ratio", "debt ratio", "debt density"
        ]):
            categories.add("TD economic/remediation metrics")

        if any(k in combined_td for k in [
            "smell", "violation", "rule", "sonarqube", "satd", "technical debt item"
        ]):
            categories.add("Smell/violation metrics")

        if not categories:
            categories.add("TD metrics")

    if is_valid_value(software_metrics):
        if any(k in combined_sw for k in [
            "loc", "sloc", "complexity", "coupling", "cohesion",
            "ck", "wmc", "cbo", "lcom", "rfc", "dit", "noc",
            "duplication", "test coverage"
        ]):
            categories.add("Static code/product metrics")

        if any(k in combined_sw for k in [
            "commit", "churn", "release", "defect", "bug", "issue",
            "developer", "contributor", "change-proneness", "fault-proneness"
        ]):
            categories.add("Process/evolution metrics")

        if not categories:
            categories.add("Software metrics")

    if is_valid_value(ai_metrics):
        categories.add("AI/performance prediction metrics")

    if not categories:
        return []

    return list(categories)


def count_metric_categories(df):
    """
    Count metric categories.
    Prefer existing cleaned metric-category column if present.
    Otherwise derive categories from TD_Metrics, Software_Metrics,
    and AI_Performance_Metrics.
    """
    metric_col = find_column(df, [
        "Metric_Category",
        "Metric_Categories",
        "Metrics_Category",
        "Metric_Category_Clean",
        "Metrics_Category_Clean"
    ])

    values = []

    if metric_col:
        print(f"[INFO] Using existing metric category column: {metric_col}")
        for value in df[metric_col]:
            values.extend(split_multivalue(value))
    else:
        print("[INFO] No Metric_Category column found. Creating metric categories from metric columns.")
        for _, row in df.iterrows():
            values.extend(make_metric_categories(row))

    return pd.Series(values).value_counts()


# =========================
# PLOTTING HELPERS
# =========================

def save_bar_chart(series, title, xlabel, filename, top_n=None):
    """Create and save horizontal bar chart."""
    if series.empty:
        print(f"[WARN] No data for {title}")
        return

    if top_n:
        series = series.head(top_n)

    series = series.sort_values(ascending=True)

    height = max(5, len(series) * 0.45)
    plt.figure(figsize=(11, height))

    bars = plt.barh(series.index, series.values)

    plt.title(title, fontsize=14, fontweight="bold")
    plt.xlabel(xlabel)
    plt.ylabel("")
    plt.grid(axis="x", linestyle="--", alpha=0.4)

    total = series.sum()

    # Extra space on the right so count labels do not get cut
    max_value = series.max()
    plt.xlim(0, max_value * 1.18)

    for bar in bars:
        width = bar.get_width()
        percentage = (width / total) * 100 if total else 0
        plt.text(
            width,
            bar.get_y() + bar.get_height() / 2,
            f" {int(width)} ({percentage:.1f}%)",
            va="center",
            fontsize=9
        )

    plt.tight_layout()

    png_path = os.path.join(OUTPUT_DIR, f"{filename}.png")
    pdf_path = os.path.join(OUTPUT_DIR, f"{filename}.pdf")

    plt.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.savefig(pdf_path, bbox_inches="tight")
    plt.close()

    print(f"[SAVED] {png_path}")
    print(f"[SAVED] {pdf_path}")


def make_pair_counts(df, row_col, col_col):
    """
    Create pair counts for heatmap from two multi-value columns.
    Example: TD_Type x Dataset_Type.
    """
    pairs = []

    for _, row in df.iterrows():
        row_values = split_multivalue(row.get(row_col, ""))
        col_values = split_multivalue(row.get(col_col, ""))

        for r in row_values:
            for c in col_values:
                pairs.append((r, c))

    if not pairs:
        return pd.DataFrame()

    pair_df = pd.DataFrame(pairs, columns=[row_col, col_col])
    matrix = pd.crosstab(pair_df[row_col], pair_df[col_col])

    return matrix


def save_heatmap(matrix, title, filename, top_rows=12, top_cols=8):
    """Create and save heatmap using matplotlib only."""
    if matrix.empty:
        print(f"[WARN] No data for heatmap: {title}")
        return

    # Keep only most frequent rows and columns for readability
    row_order = matrix.sum(axis=1).sort_values(ascending=False).head(top_rows).index
    col_order = matrix.sum(axis=0).sort_values(ascending=False).head(top_cols).index

    matrix = matrix.loc[row_order, col_order]

    plt.figure(figsize=(max(10, len(col_order) * 1.3), max(7, len(row_order) * 0.55)))

    plt.imshow(matrix.values, aspect="auto")

    plt.title(title, fontsize=14, fontweight="bold")
    plt.xticks(range(len(matrix.columns)), matrix.columns, rotation=45, ha="right")
    plt.yticks(range(len(matrix.index)), matrix.index)

    plt.colorbar(label="Number of studies")

    # Add count labels inside cells
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix.iloc[i, j]
            if value > 0:
                plt.text(j, i, str(value), ha="center", va="center", fontsize=8)

    plt.tight_layout()

    png_path = os.path.join(OUTPUT_DIR, f"{filename}.png")
    pdf_path = os.path.join(OUTPUT_DIR, f"{filename}.pdf")

    plt.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.savefig(pdf_path, bbox_inches="tight")
    plt.close()

    print(f"[SAVED] {png_path}")
    print(f"[SAVED] {pdf_path}")


# =========================
# COLUMN DETECTION
# =========================

col_empirical = find_column(df, ["Has_Empirical_Evaluation"])
col_td_type = find_column(df, ["TD_Type", "TD_Type_Clean"])
col_dataset_type = find_column(df, ["Dataset_Type", "Dataset_Type_Clean"])
col_dataset_availability = find_column(df, ["Dataset_Availability", "Dataset_Availability_Clean"])
col_validation = find_column(df, ["Validation_Method", "Validation_Method_Clean"])
col_method = find_column(df, ["Method_Type", "Method_Type_Clean"])
col_ai_metrics = find_column(df, ["AI_Performance_Metrics", "AI_Performance_Metrics_Clean"])


required = {
    "Has_Empirical_Evaluation": col_empirical,
    "TD_Type": col_td_type,
    "Dataset_Type": col_dataset_type,
    "Dataset_Availability": col_dataset_availability,
    "Validation_Method": col_validation,
    "Method_Type": col_method,
    "AI_Performance_Metrics": col_ai_metrics,
}

for name, col in required.items():
    if col is None:
        print(f"[WARN] Column not found for: {name}")
    else:
        print(f"[INFO] {name} -> {col}")


# =========================
# FIGURE 1: EMPIRICAL EVALUATION STATUS
# =========================

if col_empirical:
    empirical_counts = count_single_column(df, col_empirical)
    save_bar_chart(
        empirical_counts,
        "Empirical Evaluation Status in Technical Debt Studies",
        "Number of studies",
        "fig01_empirical_evaluation_status"
    )


# =========================
# FIGURE 2: METRIC CATEGORIES USED IN TD STUDIES
# Excluding NR/NA automatically
# =========================

metric_counts = count_metric_categories(df)
save_bar_chart(
    metric_counts,
    "Metric Categories Used in Technical Debt Studies",
    "Number of studies",
    "fig02_metric_categories_excluding_NR_NA",
    top_n=15
)


# =========================
# FIGURE 3: DATASET TYPES USED IN TD STUDIES
# =========================

if col_dataset_type:
    dataset_type_counts = count_multivalue_column(df, col_dataset_type)
    save_bar_chart(
        dataset_type_counts,
        "Dataset Types Used in Technical Debt Studies",
        "Number of studies",
        "fig03_dataset_types_excluding_NR_NA",
        top_n=15
    )


# =========================
# FIGURE 4: DATASET AVAILABILITY
# =========================

if col_dataset_availability:
    availability_counts = count_multivalue_column(df, col_dataset_availability)
    save_bar_chart(
        availability_counts,
        "Dataset Availability in Technical Debt Studies",
        "Number of studies",
        "fig04_dataset_availability_excluding_NR_NA"
    )


# =========================
# FIGURE 5: VALIDATION METHODS USED IN TD STUDIES
# =========================

if col_validation:
    validation_counts = count_multivalue_column(df, col_validation)
    save_bar_chart(
        validation_counts,
        "Validation Methods Used in Technical Debt Studies",
        "Number of studies",
        "fig05_validation_methods_excluding_NR_NA",
        top_n=15
    )


# =========================
# FIGURE 6: TD TYPE × DATASET TYPE HEATMAP
# =========================

if col_td_type and col_dataset_type:
    td_dataset_matrix = make_pair_counts(df, col_td_type, col_dataset_type)
    save_heatmap(
        td_dataset_matrix,
        "TD Type × Dataset Type",
        "fig06_td_type_by_dataset_type_heatmap",
        top_rows=12,
        top_cols=8
    )


# =========================
# FIGURE 7: TD TYPE × VALIDATION METHOD HEATMAP
# =========================

if col_td_type and col_validation:
    td_validation_matrix = make_pair_counts(df, col_td_type, col_validation)
    save_heatmap(
        td_validation_matrix,
        "TD Type × Validation Method",
        "fig07_td_type_by_validation_method_heatmap",
        top_rows=12,
        top_cols=8
    )

def normalize_ai_performance_metric(value):
    """
    Normalize duplicate/noisy AI performance metric names.
    """

    value = clean_text(value)

    if not is_valid_value(value):
        return ""

    key = value.lower().strip()
    key = re.sub(r"\s+", " ", key)
    key = key.replace("_", "-")

    # Remove fragments that are not metric names
    # Example: "range: 0.625-0.859)" should be ignored
    if key.startswith("range"):
        return ""

    # Remove reported numeric values after colon/equal sign
    # Example: "Precision: 56.66%" -> "precision"
    # Example: "Recall: 59.07%" -> "recall"
    key = re.sub(r"\s*[:=]\s*\d+(\.\d+)?%?", "", key).strip()

    # Convert phrases like "F1 score of 0.76" into "F1-score"
    if re.match(r"f1\s*score\s*of\s*\d+(\.\d+)?", key):
        return "F1-score"

    if re.match(r"f1-score\s*of\s*\d+(\.\d+)?", key):
        return "F1-score"

    # Convert phrases like "F1-score (0.712 average" into "F1-score"
    if key.startswith("f1-score") or key.startswith("f1 score") or key == "f1":
        return "F1-score"

    if key.startswith("f2-score") or key.startswith("f2 score") or key == "f2":
        return "F2-score"

    if key.startswith("f2-measure") or key.startswith("f2 measure"):
        return "F2-score"

    if key in ["false positive rate", "false-positive rate", "fpr"]:
        return "FPR"

    mapping = {
        "accuracy": "Accuracy",
        "acc": "Accuracy",
        "performance and accuracy": "Accuracy",

        "precision": "Precision",
        "prec": "Precision",

        "recall": "Recall",
        "sensitivity": "Recall",

        "f1": "F1-score",
        "f1-score": "F1-score",
        "f1 score": "F1-score",
        "f1score": "F1-score",
        "f-score": "F1-score",
        "f score": "F1-score",
        "f-measure": "F1-score",
        "f measure": "F1-score",
        "fmeasure": "F1-score",

        "f2": "F2-score",
        "f2-score": "F2-score",
        "f2 score": "F2-score",
        "f2-measure": "F2-score",

        "auc": "AUC",
        "roc-auc": "AUC",
        "roc auc": "AUC",
        "auc-roc": "AUC",
        "auroc": "AUC",
        "area under curve": "AUC",
        "area under the curve": "AUC",

        "mcc": "MCC",
        "matthews correlation coefficient": "MCC",

        "rmse": "RMSE",
        "root mean squared error": "RMSE",
        "root mean square error": "RMSE",
        "root mean squared error (rmse)": "RMSE",
        "root mean square error (rmse)": "RMSE",

        "mae": "MAE",
        "mean absolute error": "MAE",

        "mse": "MSE",
        "mean squared error": "MSE",

        "r2": "R²",
        "r2 score": "R²",
        "r2-score": "R²",
        "r-squared": "R²",
        "r squared": "R²",

        "pred25": "PRED(25)",
        "pred(25)": "PRED(25)",

        "false positive rate": "FPR",
        "false-positive rate": "FPR",
        "fpr": "FPR",
    }

    return mapping.get(key, value)

# =========================
# FIGURE 8: AI PERFORMANCE METRICS USED IN AI-BASED TD STUDIES
# =========================

def is_ai_based_row(row):
    method_text = clean_text(row.get(col_method, "")).lower() if col_method else ""
    ai_metric_text = clean_text(row.get(col_ai_metrics, "")) if col_ai_metrics else ""

    ai_keywords = [
        "machine learning",
        "deep learning",
        "nlp",
        "llm",
        "neural",
        "classification",
        "classifier",
        "random forest",
        "svm",
        "naive bayes",
        "decision tree",
        "xgboost",
        "bert",
        "cnn",
        "lstm",
        "transformer",
        "text mining",
        "ai"
    ]

    if any(keyword in method_text for keyword in ai_keywords):
        return True

    if is_valid_value(ai_metric_text):
        return True

    return False


def count_ai_performance_metrics(df, column_name):
    """
    Count AI performance metrics after normalizing duplicates.
    Splits AI metrics by semicolon, pipe, and comma.
    """

    values = []

    for value in df[column_name]:
        value = clean_text(value)

        if not is_valid_value(value):
            continue

        raw_metrics = re.split(r";|\||,", value)

        for metric in raw_metrics:
            metric = clean_text(metric)
            normalized_metric = normalize_ai_performance_metric(metric)

            if is_valid_value(normalized_metric):
                values.append(normalized_metric)

    return pd.Series(values).value_counts()

if col_ai_metrics:
    ai_df = df[df.apply(is_ai_based_row, axis=1)].copy()
    print(f"[INFO] AI-based rows detected: {len(ai_df)}")

    ai_metric_counts = count_ai_performance_metrics(ai_df, col_ai_metrics)

    save_bar_chart(
        ai_metric_counts,
        "AI Performance Metrics Used in AI-Based TD Studies",
        "Number of studies",
        "fig08_ai_performance_metrics_excluding_NR_NA",
        top_n=15
    )
print("\n[DONE] All figures generated.")
print(f"Check the folder: {OUTPUT_DIR}")