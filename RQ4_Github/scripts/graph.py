import os
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

FILE_PATH = r"RQ4 Final data used for plotting.xlsx"
SHEET_NAME = "TD_Cleaned_Long"

OUTPUT_DIR = "RQ4_Graphs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

VENUE_THRESHOLD = 10
TD_THRESHOLD = 10
TOP_TD_TYPES = 8


# ============================================================
# 1. LOAD DATA
# ============================================================

df = pd.read_excel(
    FILE_PATH,
    sheet_name=SHEET_NAME
)

print("Rows in TD_Cleaned_Long:", len(df))
print("Unique papers:", df["paper_id"].nunique())


# ============================================================
# 2. BASIC CLEANING
# ============================================================

# Convert year to numeric
df["year"] = pd.to_numeric(
    df["year"],
    errors="coerce"
)

# Remove rows without a valid year
df = df.dropna(
    subset=["year"]
).copy()

# Convert year to integer
df["year"] = df["year"].astype(int)


# ------------------------------------------------------------
# CLEAN FINAL VENUE COLUMN
# ------------------------------------------------------------

df["final venue used for plotting"] = (
    df["final venue used for plotting"]
    .fillna("Not available")
    .astype(str)
    .str.strip()
)


# ------------------------------------------------------------
# CLEAN PUBLICATION TYPE
# ------------------------------------------------------------

df["publication_type"] = (
    df["publication_type"]
    .fillna("Not available")
    .astype(str)
    .str.strip()
)


# ------------------------------------------------------------
# CLEAN TD TYPE
# ------------------------------------------------------------

df["td_types"] = (
    df["td_types"]
    .fillna("Others")
    .astype(str)
    .str.strip()
)


# ============================================================
# IMPORTANT
# ============================================================
#
# TD_Cleaned_Long contains duplicated paper IDs intentionally.
#
# Example:
#
# P003 | 2019 | Social Debt
# P003 | 2019 | Architecture Debt
#
# This means P003 investigates TWO TD types.
#
# For:
#
#   Figure 1 → Year
#   Figure 2 → Venue
#   Figure 3 → Publication type
#
# count each paper only ONCE.
#
# For:
#
#   Figure 4 → TD type distribution
#   Figure 5 → TD type evolution
#
# keep the long-format rows.
#
# ============================================================

df_papers = (
    df
    .drop_duplicates(
        subset=["paper_id"]
    )
    .copy()
)

print(
    "Rows used for paper-level plots:",
    len(df_papers)
)


# ============================================================
# FIGURE 1
# EVOLUTION OF TECHNICAL DEBT PUBLICATIONS OVER TIME
# ============================================================

year_counts = (
    df_papers
    .groupby("year")["paper_id"]
    .nunique()
    .sort_index()
)

plt.figure(
    figsize=(14, 7)
)


# ------------------------------------------------------------
# DRAW LINE
# ------------------------------------------------------------

plt.plot(
    year_counts.index,
    year_counts.values,
    marker="o",
    markersize=6,
    linewidth=2
)


# ------------------------------------------------------------
# ADD PUBLICATION COUNT ABOVE EVERY POINT
# ------------------------------------------------------------

for year, count in zip(
    year_counts.index,
    year_counts.values
):

    plt.annotate(
        str(count),
        (year, count),
        textcoords="offset points",
        xytext=(0, 8),
        ha="center",
        fontsize=8
    )


# ------------------------------------------------------------
# AXIS LABELS AND TITLE
# ------------------------------------------------------------

plt.xlabel(
    "Year",
    fontsize=12
)

plt.ylabel(
    "Number of Publications",
    fontsize=12
)

plt.title(
    "Evolution of Technical Debt Publications Over Time",
    fontsize=14
)


# ------------------------------------------------------------
# SHOW EVERY SECOND YEAR ON X-AXIS
# ------------------------------------------------------------

years = year_counts.index.tolist()

plt.xticks(
    years[::2],
    rotation=45,
    fontsize=9
)

plt.yticks(
    fontsize=10
)


# ------------------------------------------------------------
# GRID
# ------------------------------------------------------------

plt.grid(
    axis="y",
    linestyle="--",
    alpha=0.3
)


# Give enough space for count above highest point
plt.ylim(
    0,
    year_counts.max() * 1.15
)

plt.tight_layout()


# ------------------------------------------------------------
# SAVE FIGURE 1
# ------------------------------------------------------------

plt.savefig(
    os.path.join(
        OUTPUT_DIR,
        "RQ4_1_Publications_Per_Year.pdf"
    ),
    format="pdf",
    bbox_inches="tight"
)

plt.close()

print("Created Figure 1")


# ============================================================
# FIGURE 2
# DISTRIBUTION OF TECHNICAL DEBT PUBLICATIONS BY VENUE
# ONLY VENUES WITH MORE THAN 10 PAPERS
# ============================================================

# IMPORTANT:
# Column G = "final venue used for plotting"
#
# We count UNIQUE papers per venue because TD_Cleaned_Long
# contains multiple rows for papers having multiple TD types.
#
# "others" is NOT plotted as a venue.
#
# Only real venues having > 10 unique papers are shown.
# ============================================================


# ------------------------------------------------------------
# CREATE PAPER-LEVEL VENUE DATA
# ------------------------------------------------------------

venue_papers = (
    df[
        [
            "paper_id",
            "final venue used for plotting"
        ]
    ]
    .drop_duplicates(
        subset=[
            "paper_id",
            "final venue used for plotting"
        ]
    )
    .copy()
)


# ------------------------------------------------------------
# REMOVE "others" AND INVALID VALUES
# ------------------------------------------------------------

venue_papers = venue_papers[
    ~venue_papers[
        "final venue used for plotting"
    ]
    .str.strip()
    .str.lower()
    .isin([
        "others",
        "other",
        "not available",
        ""
    ])
].copy()


# ------------------------------------------------------------
# COUNT UNIQUE PAPERS FOR EACH VENUE
# ------------------------------------------------------------

venue_counts = (
    venue_papers
    .groupby(
        "final venue used for plotting"
    )["paper_id"]
    .nunique()
    .sort_values(
        ascending=False
    )
)


# ------------------------------------------------------------
# KEEP ONLY VENUES WITH COUNT > 10
# ------------------------------------------------------------

venue_counts_major = venue_counts[
    venue_counts > VENUE_THRESHOLD
].copy()


# ------------------------------------------------------------
# PRINT RESULT TO TERMINAL
# ------------------------------------------------------------

print(
    "\n=============================================="
)

print(
    "VENUES WITH MORE THAN "
    f"{VENUE_THRESHOLD} PAPERS"
)

print(
    "=============================================="
)

print(
    venue_counts_major
)

print(
    "\nNumber of venues shown:",
    len(venue_counts_major)
)


# ------------------------------------------------------------
# OPTIONAL CHECK AGAINST EXISTING 'count' COLUMN
# ------------------------------------------------------------

if "count" in df.columns:

    count_check = (
        df[
            ~df[
                "final venue used for plotting"
            ]
            .str.strip()
            .str.lower()
            .isin([
                "others",
                "other",
                "not available",
                ""
            ])
        ]
        .groupby(
            "final venue used for plotting"
        )["count"]
        .max()
        .sort_values(
            ascending=False
        )
    )

    print(
        "\nExisting values from Excel 'count' column:"
    )

    print(
        count_check[
            count_check > VENUE_THRESHOLD
        ]
    )


# ------------------------------------------------------------
# SORT FOR HORIZONTAL BAR GRAPH
# smallest at bottom, largest at top
# ------------------------------------------------------------

venue_plot = (
    venue_counts_major
    .sort_values(
        ascending=True
    )
)


# ------------------------------------------------------------
# CREATE GRAPH
# ------------------------------------------------------------

figure_height = max(
    7,
    len(venue_plot) * 0.55
)

plt.figure(
    figsize=(
        14,
        figure_height
    )
)


bars = plt.barh(
    venue_plot.index,
    venue_plot.values
)


# ------------------------------------------------------------
# ADD COUNT TO END OF EACH BAR
# ------------------------------------------------------------

for bar in bars:

    count = int(
        bar.get_width()
    )

    plt.text(
        bar.get_width() + 0.5,
        bar.get_y()
        + bar.get_height() / 2,
        str(count),
        va="center",
        ha="left",
        fontsize=10
    )


# ------------------------------------------------------------
# LABELS
# ------------------------------------------------------------

plt.xlabel(
    "Number of Publications",
    fontsize=12
)

plt.ylabel(
    "Venue",
    fontsize=12
)

plt.title(
    "Major Publication Venues in Technical Debt Research",
    fontsize=14
)


# ------------------------------------------------------------
# GIVE SPACE FOR NUMBERS
# ------------------------------------------------------------

if len(venue_plot) > 0:

    plt.xlim(
        0,
        venue_plot.max() * 1.12
    )


plt.grid(
    axis="x",
    linestyle="--",
    alpha=0.25
)


plt.tight_layout()


# ------------------------------------------------------------
# SAVE GRAPH
# ------------------------------------------------------------

plt.savefig(
    os.path.join(
        OUTPUT_DIR,
        "RQ4_2_Publications_By_Venue.pdf"
    ),
    format="pdf",
    bbox_inches="tight"
)

plt.close()


print(
    "\nCreated corrected Figure 2"
)


# ============================================================
# FIGURE 3
# EVOLUTION OF PUBLICATION TYPES OVER TIME
# LINE CHART + SIGNIFICANT POINTS
# ============================================================


# ------------------------------------------------------------
# COUNT UNIQUE PAPERS PER YEAR × PUBLICATION TYPE
# ------------------------------------------------------------

pub_year = (
    df_papers
    .groupby(
        [
            "year",
            "publication_type"
        ]
    )["paper_id"]
    .nunique()
    .unstack(
        fill_value=0
    )
    .sort_index()
)


# ------------------------------------------------------------
# REMOVE UNWANTED PUBLICATION TYPES
# ------------------------------------------------------------

columns_to_remove = [
    "Not available"
]

pub_year_plot = pub_year.drop(
    columns=columns_to_remove,
    errors="ignore"
)


# ------------------------------------------------------------
# CREATE CONTINUOUS YEAR RANGE
# ------------------------------------------------------------
# This is important because otherwise pandas compares
# consecutive rows rather than consecutive calendar years.
#
# Example:
# 1992 -> 2001 would otherwise be treated as one step.
# ------------------------------------------------------------

all_years = range(
    pub_year_plot.index.min(),
    pub_year_plot.index.max() + 1
)

pub_year_plot = (
    pub_year_plot
    .reindex(
        all_years,
        fill_value=0
    )
)


# ============================================================
# PRINT FULL COUNTS
# ============================================================

print(
    "\n=============================================="
)

print(
    "PUBLICATION TYPE COUNTS BY YEAR"
)

print(
    "=============================================="
)

print(
    pub_year_plot
)


# ============================================================
# SIGNIFICANT POINTS
# ============================================================

print(
    "\n=============================================="
)

print(
    "SIGNIFICANT POINTS BY PUBLICATION TYPE"
)

print(
    "=============================================="
)


for publication_type in pub_year_plot.columns:

    series = (
        pub_year_plot[
            publication_type
        ]
    )


    # --------------------------------------------------------
    # FIRST APPEARANCE
    # --------------------------------------------------------

    non_zero = series[
        series > 0
    ]

    if len(non_zero) > 0:

        first_year = (
            non_zero.index[0]
        )

        first_count = int(
            non_zero.iloc[0]
        )

    else:

        first_year = "Not available"

        first_count = 0


    # --------------------------------------------------------
    # PEAK
    # --------------------------------------------------------

    peak_count = int(
        series.max()
    )

    peak_years = (
        series[
            series == peak_count
        ]
        .index
        .tolist()
    )


    # --------------------------------------------------------
    # YEAR-TO-YEAR CHANGE
    # --------------------------------------------------------

    yearly_change = (
        series.diff()
    )


    # --------------------------------------------------------
    # BIGGEST INCREASE
    # --------------------------------------------------------

    valid_increases = (
        yearly_change
        .dropna()
    )

    if not valid_increases.empty:

        increase_year = (
            valid_increases.idxmax()
        )

        increase_value = int(
            valid_increases.max()
        )

        previous_increase_year = (
            increase_year - 1
        )

        previous_increase_count = int(
            series.loc[
                previous_increase_year
            ]
        )

        increase_count = int(
            series.loc[
                increase_year
            ]
        )

    else:

        increase_year = "Not available"

        increase_value = 0

        previous_increase_year = (
            "Not available"
        )

        previous_increase_count = 0

        increase_count = 0


    # --------------------------------------------------------
    # BIGGEST DECREASE
    # --------------------------------------------------------

    if not valid_increases.empty:

        decrease_year = (
            valid_increases.idxmin()
        )

        decrease_value = int(
            valid_increases.min()
        )

        previous_decrease_year = (
            decrease_year - 1
        )

        previous_decrease_count = int(
            series.loc[
                previous_decrease_year
            ]
        )

        decrease_count = int(
            series.loc[
                decrease_year
            ]
        )

    else:

        decrease_year = "Not available"

        decrease_value = 0

        previous_decrease_year = (
            "Not available"
        )

        previous_decrease_count = 0

        decrease_count = 0


    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    print()

    print(
        publication_type
    )

    print(
        f"  First appearance: "
        f"{first_year} "
        f"({first_count} publication(s))"
    )

    print(
        f"  Peak: "
        f"{', '.join(map(str, peak_years))} "
        f"({peak_count} publication(s))"
    )

    print(
        f"  Biggest annual increase: "
        f"{previous_increase_year} -> "
        f"{increase_year} "
        f"({previous_increase_count} -> "
        f"{increase_count}, "
        f"+{increase_value})"
    )

    print(
        f"  Biggest annual decrease: "
        f"{previous_decrease_year} -> "
        f"{decrease_year} "
        f"({previous_decrease_count} -> "
        f"{decrease_count}, "
        f"{decrease_value})"
    )


# ============================================================
# CREATE FIGURE
# ============================================================

plt.figure(
    figsize=(14, 8)
)


# ------------------------------------------------------------
# DRAW ONE LINE PER PUBLICATION TYPE
# ------------------------------------------------------------

for publication_type in pub_year_plot.columns:

    plt.plot(
        pub_year_plot.index,
        pub_year_plot[
            publication_type
        ],
        marker="o",
        markersize=5,
        linewidth=2,
        label=publication_type
    )


# ------------------------------------------------------------
# LABELS
# ------------------------------------------------------------

plt.xlabel(
    "Year",
    fontsize=12
)

plt.ylabel(
    "Number of Publications",
    fontsize=12
)

plt.title(
    "Evolution of Publication Types in Technical Debt Research",
    fontsize=14
)


# ------------------------------------------------------------
# X AXIS
# ------------------------------------------------------------

years = (
    pub_year_plot
    .index
    .tolist()
)

plt.xticks(
    years[::2],
    rotation=45,
    fontsize=9
)


# ------------------------------------------------------------
# GRID
# ------------------------------------------------------------

plt.grid(
    axis="y",
    linestyle="--",
    alpha=0.3
)


# ------------------------------------------------------------
# LEGEND
# ------------------------------------------------------------

plt.legend(
    title="Publication Type",
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)


# ------------------------------------------------------------
# LAYOUT
# ------------------------------------------------------------

plt.tight_layout()


# ------------------------------------------------------------
# SAVE FIGURE
# ------------------------------------------------------------

plt.savefig(
    os.path.join(
        OUTPUT_DIR,
        "RQ4_3_Publication_Type_Over_Time.pdf"
    ),
    format="pdf",
    bbox_inches="tight"
)

plt.close()


print()

print(
    "Created Figure 3:"
)

print(
    "RQ4_3_Publication_Type_Over_Time.pdf"
)
# ============================================================
# FIGURE 4
# TD TYPE DISTRIBUTION
# SHOW ALL TD TYPES SEPARATELY
# ============================================================

# A paper may investigate multiple TD types.
# Therefore, one paper can contribute once to several TD types.
#
# nunique() ensures that the same paper is counted only once
# within the same TD type.
# ============================================================


# ------------------------------------------------------------
# COUNT UNIQUE PAPERS PER TD TYPE
# ------------------------------------------------------------

td_counts = (
    df
    .groupby(
        "td_types"
    )["paper_id"]
    .nunique()
    .sort_values(
        ascending=False
    )
)


# ------------------------------------------------------------
# PRINT ALL TD TYPES AND COUNTS
# ------------------------------------------------------------

print(
    "\n=============================================="
)

print(
    "ALL TD TYPE COUNTS"
)

print(
    "=============================================="
)

print(
    td_counts
)

print(
    "\nNumber of distinct TD types:",
    len(td_counts)
)


# ------------------------------------------------------------
# OPTIONAL:
# PRINT TOTAL PAPER-TD TYPE ASSIGNMENTS
# ------------------------------------------------------------

print(
    "\nTotal paper-TD type assignments:",
    td_counts.sum()
)

print(
    "Unique papers in corpus:",
    df["paper_id"].nunique()
)

print(
    "\nNote: Assignment total can be greater than the corpus "
    "because one paper may investigate multiple TD types."
)


# ------------------------------------------------------------
# USE ALL TD TYPES
# ------------------------------------------------------------

td_plot = (
    td_counts
    .sort_values(
        ascending=True
    )
)


# ------------------------------------------------------------
# AUTOMATIC FIGURE HEIGHT
# ------------------------------------------------------------

figure_height = max(
    9,
    len(td_plot) * 0.45
)


# ------------------------------------------------------------
# CREATE FIGURE
# ------------------------------------------------------------

plt.figure(
    figsize=(
        13,
        figure_height
    )
)


bars = plt.barh(
    td_plot.index,
    td_plot.values
)


# ------------------------------------------------------------
# ADD COUNT AT END OF EACH BAR
# ------------------------------------------------------------

for bar in bars:

    width = bar.get_width()

    plt.text(
        width + 1,
        bar.get_y()
        + bar.get_height() / 2,
        f"{int(width)}",
        va="center",
        ha="left",
        fontsize=9
    )


# ------------------------------------------------------------
# LABELS
# ------------------------------------------------------------

plt.xlabel(
    "Number of Papers",
    fontsize=12
)

plt.ylabel(
    "Technical Debt Type",
    fontsize=12
)

plt.title(
    "Distribution of Technical Debt Types",
    fontsize=14
)


# ------------------------------------------------------------
# GRID
# ------------------------------------------------------------

plt.grid(
    axis="x",
    linestyle="--",
    alpha=0.25
)


# ------------------------------------------------------------
# SPACE FOR COUNT LABELS
# ------------------------------------------------------------

if len(td_plot) > 0:

    plt.xlim(
        0,
        td_plot.max() * 1.12
    )


plt.tight_layout()


# ------------------------------------------------------------
# SAVE FIGURE
# ------------------------------------------------------------

plt.savefig(
    os.path.join(
        OUTPUT_DIR,
        "RQ4_4_TD_Type_Distribution.pdf"
    ),
    format="pdf",
    bbox_inches="tight"
)

plt.close()


print(
    "\nCreated Figure 4 with all TD types."
)
# ============================================================
# FIGURE 5
# TD TYPE EVOLUTION OVER TIME
# ============================================================

# Select the top TD types overall.
#
# Exclude Others.
# ============================================================

top_td_types = (
    td_counts
    .drop(
        labels=["Others"],
        errors="ignore"
    )
    .head(
        TOP_TD_TYPES
    )
    .index
    .tolist()
)


print(
    "\nTD types used for evolution graph:"
)


for td in top_td_types:

    print(
        " -",
        td
    )


# ------------------------------------------------------------
# FILTER TOP TD TYPES
# ------------------------------------------------------------

td_evolution = df[
    df["td_types"].isin(
        top_td_types
    )
].copy()


# ------------------------------------------------------------
# COUNT UNIQUE PAPERS PER YEAR × TD TYPE
# ------------------------------------------------------------

td_year = (
    td_evolution
    .groupby(
        [
            "year",
            "td_types"
        ]
    )["paper_id"]
    .nunique()
    .unstack(
        fill_value=0
    )
)


# ------------------------------------------------------------
# PLOT
# ------------------------------------------------------------

plt.figure(
    figsize=(14, 8)
)


for td_type in td_year.columns:

    plt.plot(
        td_year.index,
        td_year[td_type],
        marker="o",
        linewidth=2,
        label=td_type
    )


plt.xlabel(
    "Year"
)

plt.ylabel(
    "Number of Papers"
)

plt.title(
    "Evolution of Major Technical Debt Types Over Time"
)


plt.legend(
    title="Technical Debt Type",
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)


plt.grid(
    axis="y",
    linestyle="--",
    alpha=0.3
)


# Show every second year
td_years = (
    td_year
    .index
    .tolist()
)

plt.xticks(
    td_years[::2],
    rotation=45
)


plt.tight_layout()


plt.savefig(
    os.path.join(
        OUTPUT_DIR,
        "RQ4_5_TD_Type_Evolution.pdf"
    ),
    format="pdf",
    bbox_inches="tight"
)

plt.close()

print("Created Figure 5")


# ============================================================
# SAVE PLOT DATA TO EXCEL
# ============================================================

output_excel = os.path.join(
    OUTPUT_DIR,
    "RQ4_Plot_Data.xlsx"
)


with pd.ExcelWriter(
    output_excel,
    engine="openpyxl"
) as writer:

    # --------------------------------------------------------
    # YEAR COUNTS
    # --------------------------------------------------------

    year_counts.to_excel(
        writer,
        sheet_name="Year_Counts",
        header=["Count"]
    )


    # --------------------------------------------------------
    # VENUE COUNTS
    # --------------------------------------------------------

    venue_counts.to_excel(
        writer,
        sheet_name="Venue_Counts",
        header=["Count"]
    )


    # --------------------------------------------------------
    # PUBLICATION TYPE × YEAR
    # --------------------------------------------------------

    pub_year.to_excel(
        writer,
        sheet_name="Publication_Type_Year"
    )


    # --------------------------------------------------------
    # TD TYPE COUNTS
    # --------------------------------------------------------

    td_counts.to_excel(
        writer,
        sheet_name="TD_Type_Counts",
        header=["Count"]
    )


    # --------------------------------------------------------
    # TD TYPE × YEAR
    # --------------------------------------------------------

    td_year.to_excel(
        writer,
        sheet_name="TD_Type_Year"
    )


# ============================================================
# FINAL MESSAGE
# ============================================================

print(
    "\n===================================="
)

print(
    "ALL GRAPHS GENERATED SUCCESSFULLY"
)

print(
    "===================================="
)


print(
    "\nGraphs saved in folder:",
    os.path.abspath(
        OUTPUT_DIR
    )
)


print(
    "\nPlot data saved as:",
    output_excel
)