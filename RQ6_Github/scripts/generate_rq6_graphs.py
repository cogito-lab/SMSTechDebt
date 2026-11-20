import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Change this if your Excel file name is different
EXCEL_FILE = "output/RQ6_Final_Graph_6th_round.xlsx"
OUTPUT_DIR = Path("RQ6_Graphs")
OUTPUT_DIR.mkdir(exist_ok=True)

plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["font.size"] = 11


def format_count(value):
    """Format count labels cleanly as integers when possible."""
    if float(value).is_integer():
        return str(int(value))
    return str(round(value, 2))


def save_bar_chart(df, x_col, y_col, title, xlabel, ylabel, filename, top_n=None):
    data = df[[x_col, y_col]].dropna().copy()
    data[y_col] = pd.to_numeric(data[y_col], errors="coerce")
    data = data.dropna(subset=[y_col])
    data = data.sort_values(y_col, ascending=False)

    if top_n:
        data = data.head(top_n)

    # Sort ascending so the largest bar appears at the top in horizontal bar chart
    data = data.sort_values(y_col, ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(data[x_col], data[y_col])

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    # Add count labels at the end of each bar
    max_value = data[y_col].max()
    ax.set_xlim(0, max_value * 1.15)

    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + (max_value * 0.01),
            bar.get_y() + bar.get_height() / 2,
            format_count(width),
            va="center",
            ha="left",
            fontsize=10
        )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{filename}.png", bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / f"{filename}.pdf", bbox_inches="tight")
    plt.close()


# Load sheets
ai_df = pd.read_excel(EXCEL_FILE, sheet_name="Graph_AI_Category")
td_df = pd.read_excel(EXCEL_FILE, sheet_name="Graph_TD_Type")
algo_df = pd.read_excel(EXCEL_FILE, sheet_name="Algorithm_Frequency_Clean")
cross_df = pd.read_excel(EXCEL_FILE, sheet_name="Graph_AI_vs_TD")
clean_df = pd.read_excel(EXCEL_FILE, sheet_name="Final_Cleaned")


# Figure 6.1: AI category distribution
save_bar_chart(
    ai_df,
    x_col="AI_Category",
    y_col="Count",
    title="Distribution of AI-Based Approaches",
    xlabel="Number of studies",
    ylabel="AI category",
    filename="Figure_6_1_AI_Category_Distribution"
)


# Figure 6.2: TD type distribution
save_bar_chart(
    td_df,
    x_col="TD_Type",
    y_col="Count",
    title="Targeted Technical Debt Types",
    xlabel="Number of studies",
    ylabel="Technical debt type",
    filename="Figure_6_2_TD_Type_Distribution"
)


# Figure 6.3: Algorithm/model frequency
save_bar_chart(
    algo_df,
    x_col="Algorithm",
    y_col="Frequency",
    title="Most Frequently Used Algorithms and Models",
    xlabel="Number of studies",
    ylabel="Algorithm / model",
    filename="Figure_6_3_Algorithm_Frequency",
    top_n=15
)


# Figure 6.4: AI category × TD type stacked bar
cross = cross_df.set_index("AI_Category_Final")
cross = cross.apply(pd.to_numeric, errors="coerce").fillna(0)

fig, ax = plt.subplots(figsize=(12, 7))
cross.plot(kind="bar", stacked=True, ax=ax)

ax.set_xlabel("AI category")
ax.set_ylabel("Number of studies")
ax.set_title("AI Category by Targeted Technical Debt Type")
ax.set_xticklabels(ax.get_xticklabels(), rotation=35, ha="right")
ax.legend(title="TD type", bbox_to_anchor=(1.05, 1), loc="upper left")

# Add count labels inside each stacked segment
for patch in ax.patches:
    height = patch.get_height()

    if height > 0:
        x = patch.get_x() + patch.get_width() / 2
        y = patch.get_y() + height / 2

        ax.text(
            x,
            y,
            format_count(height),
            ha="center",
            va="center",
            fontsize=8
        )

# Add total count labels above each stacked bar
totals = cross.sum(axis=1)

for i, total in enumerate(totals):
    ax.text(
        i,
        total + 1,
        format_count(total),
        ha="center",
        va="bottom",
        fontsize=10
    )

ax.set_ylim(0, totals.max() * 1.15)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "Figure_6_4_AI_Category_vs_TD_Type.png", bbox_inches="tight")
plt.savefig(OUTPUT_DIR / "Figure_6_4_AI_Category_vs_TD_Type.pdf", bbox_inches="tight")
plt.close()


# Figure 6.5: Publication trend by year
year_df = clean_df.copy()
year_df["year"] = pd.to_numeric(year_df["year"], errors="coerce")

year_counts = (
    year_df
    .dropna(subset=["year"])["year"]
    .astype(int)
    .value_counts()
    .sort_index()
)

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(year_counts.index, year_counts.values, marker="o")

ax.set_xlabel("Year")
ax.set_ylabel("Number of studies")
ax.set_title("Publication Trend of AI-Based TD Detection Studies")
ax.set_xticks(year_counts.index)
ax.set_xticklabels(year_counts.index, rotation=45)

# Add count labels above each point
max_count = year_counts.max()
ax.set_ylim(0, max_count * 1.2)

for year, count in zip(year_counts.index, year_counts.values):
    ax.text(
        year,
        count + (max_count * 0.03),
        str(count),
        ha="center",
        va="bottom",
        fontsize=9
    )

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "Figure_6_5_Publication_Trend.png", bbox_inches="tight")
plt.savefig(OUTPUT_DIR / "Figure_6_5_Publication_Trend.pdf", bbox_inches="tight")
plt.close()


print("Graphs generated successfully in:", OUTPUT_DIR.resolve())