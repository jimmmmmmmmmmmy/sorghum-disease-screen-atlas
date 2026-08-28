#!/usr/bin/env python3
"""Generate the four v23 Atlas figures from the supplied CSV files.

Example
-------
python generate_figures.py --data-dir figure_data --output-dir figures

Required input files
--------------------
Figure_1_source_data.csv
Figure_2_repeated_identification_source_data.csv
Figure_3_disease_overlap_source_data.csv
Figure_S1_Pareto_source_data.csv

It requires Python 3.11 or later, Matplotlib, NumPy, and Pillow. The program
verifies the installed Arial regular and bold faces before drawing the figures.
"""

from __future__ import annotations

import argparse
import csv
from io import BytesIO
import os
from pathlib import Path
import textwrap

# Stabilize vector metadata when the environment honors SOURCE_DATE_EPOCH.
os.environ.setdefault("SOURCE_DATE_EPOCH", "1787529600")  # 2026-08-24 UTC

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402


FONT_NAME = "Arial"
INK = "#1A1A1A"
BLUE = "#0072B2"
ORANGE = "#D55E00"
GOLD = "#E69F00"
GRAY = "#7A7A7A"
LIGHT_GRAY = "#D9D9D9"
PALE_BLUE = "#E3F1F8"
PALE_ORANGE = "#FBE8DF"
GRID = "#D9D9D9"

INPUT_FILES = {
    "1": "Figure_1_source_data.csv",
    "2": "Figure_2_repeated_identification_source_data.csv",
    "3": "Figure_3_disease_overlap_source_data.csv",
    "S1": "Figure_S1_Pareto_source_data.csv",
}

FIGURE_S1_CAPTION = (
    "Figure S1. Numbers of accessions or lines assessed and on the Pareto front in 26 sorghum "
    "disease-response analyses. Each point represents an analysis. An accession "
    "or line was on the Pareto front when no other accession or line performed "
    "at least as well on every response and better on at least one. The axes give "
    "the numbers assessed and on the Pareto front on logarithmic scales. Across "
    "the 26 analyses, the counts on the Pareto front summed to "
    "439. Symbol "
    "shape and color show the "
    "number of diseases examined; symbol size shows the number of response "
    "measures. Symbols for analyses with the same counts are separated for "
    "clarity. Table S8 lists the exact counts."
)

EXPECTED_COLUMNS = {
    "1": {"Panel", "Label", "Count", "Source and counting rule"},
    "2": {
        "Panel",
        "Measure",
        "Value",
        "Central 95% interval, lower limit",
        "Central 95% interval, upper limit",
        "Unit",
    },
    "3": {
        "Analysis identifier",
        "Study",
        "Met the study criterion for zero diseases (n)",
        "Met the study criterion for one disease (n)",
        "Met the study criterion for two or more diseases (n)",
        "Accessions or lines assessed (n)",
        "Source and classification rule",
    },
    "S1": {
        "Pareto analysis identifier",
        "Source dataset identifier",
        "Accessions or lines assessed (n)",
        "Accessions or lines on the Pareto front (n)",
        "Response measures (n)",
        "Diseases examined (n)",
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_csv_rows(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required CSV file for figure drawing not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = required_columns - columns
        require(not missing, f"{path.name} is missing columns: {sorted(missing)}")
        rows = list(reader)
    require(bool(rows), f"{path.name} contains no observations")
    return rows


def number(row: dict[str, str], column: str, *, context: str) -> float:
    raw = row.get(column, "").strip()
    require(raw != "", f"Missing {column!r} in {context}")
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid number {raw!r} for {column!r} in {context}") from exc


def integer(row: dict[str, str], column: str, *, context: str) -> int:
    value = number(row, column, context=context)
    require(value.is_integer(), f"Expected an integer for {column!r} in {context}; found {value}")
    return int(value)


def require_arial() -> None:
    """Require genuine Arial regular and bold faces before drawing anything."""

    regular = font_manager.FontProperties(family=FONT_NAME, weight="normal")
    bold = font_manager.FontProperties(family=FONT_NAME, weight="bold")
    try:
        font_manager.findfont(regular, fallback_to_default=False)
        font_manager.findfont(bold, fallback_to_default=False)
    except ValueError as exc:
        raise RuntimeError(
            "Arial regular and Arial bold are required to match the manuscript. "
            "Install Arial, clear the Matplotlib font cache if necessary, and rerun."
        ) from exc


def configure_matplotlib() -> None:
    require_arial()
    plt.rcParams.update(
        {
            "font.family": FONT_NAME,
            "font.sans-serif": [FONT_NAME],
            "font.size": 9.0,
            "axes.titlesize": 9.0,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "Matplotlib figure generator for Atlas manuscript v23",
            "savefig.facecolor": "white",
            "savefig.edgecolor": "white",
        }
    )


def box_axes(axis) -> None:
    """Apply the complete thin graph box used by the main v23 figures."""

    for spine in axis.spines.values():
        spine.set_visible(True)
        spine.set_color(INK)
        spine.set_linewidth(0.8)


def add_panel_label(axis, label: str, *, x: float = -0.14, y: float = 1.12) -> None:
    axis.text(
        x,
        y,
        label,
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=14,
        fontweight="bold",
        fontfamily=FONT_NAME,
        clip_on=False,
    )


def style_supplement_axis(axis, *, grid_axis: str = "both") -> None:
    """Apply the single-panel Figure S1 axis treatment."""

    box_axes(axis)
    axis.grid(axis=grid_axis, color=GRID, linewidth=0.65, zorder=0)
    axis.set_axisbelow(True)


def save_main_figure(figure, output_dir: Path, number_text: str, title: str) -> None:
    """Write one vector PDF and one APS-ready RGB LZW TIFF."""

    pdf_path = output_dir / f"Figure_{number_text}.pdf"
    tiff_path = output_dir / f"Figure_{number_text}.tif"
    creator = f"Matplotlib {matplotlib.__version__}"
    figure.savefig(
        pdf_path,
        format="pdf",
        facecolor="white",
        metadata={"Title": title, "Creator": creator},
    )
    raster = BytesIO()
    figure.savefig(
        raster,
        format="png",
        dpi=600,
        facecolor="white",
        metadata={"Title": title, "Software": creator},
    )
    raster.seek(0)
    with Image.open(raster) as image:
        image.convert("RGB").save(
            tiff_path,
            format="TIFF",
            compression="tiff_lzw",
            dpi=(600, 600),
        )
    plt.close(figure)


def generate_figure_1(rows: list[dict[str, str]], output_dir: Path) -> None:
    selection_rows = [row for row in rows if row["Panel"] == "A"]
    coverage_rows = [row for row in rows if row["Panel"] == "B"]
    lineage_rows = [row for row in rows if row["Panel"] == "C"]
    require(len(selection_rows) == 4, "Figure 1 panel A must describe four categories")
    require(len(coverage_rows) == 11, "Figure 1 panel B must describe eleven diseases")
    require(len(lineage_rows) == 8, "Figure 1 panel C must describe eight quantities")

    selection = {
        row["Label"]: integer(row, "Count", context=f"Figure 1 panel A category {row['Label']!r}")
        for row in selection_rows
    }
    expected_selection = {
        "Sources receiving detailed review": 149,
        "Sources contributing quantitative disease data": 76,
        "Sources requiring additional data or documentation": 38,
        "Contextual or nonquantitative sources": 35,
    }
    require(selection == expected_selection, f"Unexpected Figure 1 panel A counts: {selection}")

    coverage_labels = [row["Label"] for row in coverage_rows]
    coverage_counts = [
        integer(row, "Count", context=f"Figure 1 panel B disease {row['Label']!r}")
        for row in coverage_rows
    ]
    require(coverage_labels[0:2] == ["Anthracnose", "Grain mold and seed quality"], "Figure 1 disease order changed")
    require(coverage_counts[0:2] == [39, 19], "Figure 1 leading disease counts changed")

    lineage_counts = [
        integer(row, "Count", context=f"Figure 1 panel C label {row['Label']!r}")
        for row in lineage_rows
    ]
    expected_lineage = [149, 76, 82, 70, 34, 1154, 612, 171]
    require(lineage_counts == expected_lineage, f"Unexpected Figure 1 panel C values: {lineage_counts}")

    figure = plt.figure(figsize=(7.0, 7.7), facecolor="white")
    grid = figure.add_gridspec(2, 2, height_ratios=[1.18, 1.82], width_ratios=[0.84, 1.36])
    left = figure.add_subplot(grid[0, 0])
    right = figure.add_subplot(grid[0, 1])
    flow = figure.add_subplot(grid[1, :])

    categories = [
        "Sources contributing quantitative disease data",
        "Sources requiring additional data or documentation",
        "Contextual or nonquantitative sources",
    ]
    labels = [
        "Sources\ncontributing\nquantitative\ndisease data",
        "Data or\ndocumentation\nincomplete",
        "Contextual or\nnonquantitative\nsources",
    ]
    counts = [selection[label] for label in categories]
    bars = left.barh(np.arange(3), counts, color=[BLUE, GOLD, GRAY], height=0.58)
    left.set_yticks([])
    left.invert_yaxis()
    left.set_xlim(0, 142)
    left.set_xticks([0, 40, 80, 120])
    left.set_xlabel("Sources (n)")
    left.set_title("Sources reviewed (n = 149)", loc="left", fontweight="bold")
    add_panel_label(left, "A")
    box_axes(left)
    left.grid(axis="x", color="#DDDDDD", linewidth=0.6)
    left.set_axisbelow(True)
    for bar, count, label, text_color in zip(
        bars,
        counts,
        labels,
        ["white", INK, "white"],
        strict=True,
    ):
        left.text(
            count - 3,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            ha="right",
            va="center",
            fontweight="bold",
            color=text_color,
        )
        left.text(
            count + 3,
            bar.get_y() + bar.get_height() / 2,
            label,
            ha="left",
            va="center",
            fontsize=8.4,
        )

    coverage_display = {
        "Grain mold and seed quality": "Grain mold or seed quality",
        "Multiple diseases reported as a composite": "Multiple diseases\n(composite)",
    }
    display = [coverage_display.get(label, label) for label in coverage_labels]
    positions = np.arange(len(coverage_rows))
    bars = right.barh(positions, coverage_counts, color=BLUE, height=0.62)
    right.set_yticks(positions, display)
    right.invert_yaxis()
    right.set_xlim(0, 43)
    right.set_xlabel("Datasets (n)")
    right.set_title("Quantitative datasets by disease", loc="left", fontweight="bold")
    add_panel_label(right, "B")
    box_axes(right)
    right.grid(axis="x", color="#DDDDDD", linewidth=0.6)
    right.set_axisbelow(True)
    for bar, count in zip(bars, coverage_counts, strict=True):
        right.text(
            count + 0.6,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            va="center",
            fontweight="bold",
        )

    flow.set_xlim(0, 1)
    flow.set_ylim(0, 1)
    flow.axis("off")
    flow.set_title(
        "Sources, disease screens, and repeatedly identified candidates",
        loc="left",
        fontweight="bold",
        pad=2,
    )
    add_panel_label(flow, "C", x=-0.08)
    lineage_display = [
        "Sources reviewed",
        "Datasets with quantitative disease responses",
        "Distinct experiments or assays",
        "Distinct disease screens after reports using\nthe same measurements were combined",
        "Disease screens with matched accessions or lines\nand documented criteria",
        "Accessions or lines assessed in at least two\ndisease screens",
        "Candidates identified at least once",
        "Candidates identified in at least two disease screens",
    ]
    ys = np.linspace(0.87, 0.08, len(lineage_counts))
    box_x = 0.11
    box_width = 0.78
    box_height = 0.09
    for index, ((count, label), y_position) in enumerate(
        zip(zip(lineage_counts, lineage_display, strict=True), ys, strict=True)
    ):
        patch = FancyBboxPatch(
            (box_x, y_position - box_height / 2),
            box_width,
            box_height,
            boxstyle="round,pad=0.006,rounding_size=0.012",
            facecolor=PALE_BLUE if index < 4 else PALE_ORANGE,
            edgecolor="#6B7280",
            linewidth=0.8,
        )
        flow.add_patch(patch)
        flow.text(
            box_x + 0.095,
            y_position,
            f"{count:,}",
            ha="center",
            va="center",
            fontweight="bold",
        )
        flow.text(box_x + 0.205, y_position, label, ha="left", va="center")
        if index < len(lineage_counts) - 1:
            next_y = ys[index + 1]
            flow.annotate(
                "",
                xy=(0.5, next_y + box_height / 2 + 0.006),
                xytext=(0.5, y_position - box_height / 2 - 0.006),
                arrowprops={"arrowstyle": "-|>", "color": "#4B5563", "lw": 0.9, "mutation_scale": 8},
            )

    figure.subplots_adjust(left=0.12, right=0.985, top=0.94, bottom=0.035, hspace=0.34, wspace=0.78)
    save_main_figure(figure, output_dir, "1", "Sorghum disease screens and repeatedly identified candidates")


def generate_figure_2(rows: list[dict[str, str]], output_dir: Path) -> None:
    by_measure = {row["Measure"]: row for row in rows}
    expected_measures = {
        "Identified in one independent screen",
        "Identified in at least two independent screens",
        "Candidates identified repeatedly",
        "Permutation median and central 95% interval",
    }
    require(set(by_measure) == expected_measures, f"Unexpected Figure 2 measures: {sorted(by_measure)}")
    marks = [
        int(number(by_measure["Identified in one independent screen"], "Value", context="Figure 2 one-screen count")),
        int(number(by_measure["Identified in at least two independent screens"], "Value", context="Figure 2 repeated count")),
    ]
    interval = by_measure["Permutation median and central 95% interval"]
    observed = number(by_measure["Candidates identified repeatedly"], "Value", context="Figure 2 observed proportion") * 100
    median = number(interval, "Value", context="Figure 2 permutation median") * 100
    lower = number(interval, "Central 95% interval, lower limit", context="Figure 2 lower interval") * 100
    upper = number(interval, "Central 95% interval, upper limit", context="Figure 2 upper interval") * 100
    require(marks == [441, 171] and sum(marks) == 612, f"Unexpected Figure 2 candidate counts: {marks}")
    expected = [27.941176470588236, 21.47239263803681, 19.148936170212767, 23.809523809523807]
    require(np.allclose([observed, median, lower, upper], expected, rtol=0, atol=1e-12), "Figure 2 permutation values changed")

    figure, (left, right) = plt.subplots(
        1,
        2,
        figsize=(7.0, 4.25),
        gridspec_kw={"width_ratios": [1.02, 1.0]},
        facecolor="white",
    )
    x = np.arange(2)
    labels = ["Identified in one\ndisease screen", "Identified in at least\ntwo disease screens"]
    bars = left.bar(x, marks, color=[BLUE, ORANGE], edgecolor="white", linewidth=0.8, width=0.62)
    left.set_xticks(x, labels)
    left.set_ylim(0, 525)
    left.set_yticks([0, 200, 400])
    left.set_ylabel("Candidate accessions or lines (n)", labelpad=2)
    left.set_title("Candidates identified in one or more screens", loc="left", pad=5, fontweight="bold")
    add_panel_label(left, "A")
    for bar, value in zip(bars, marks, strict=True):
        left.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 14,
            str(value),
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    box_axes(left)
    left.grid(axis="y", color=GRID, linewidth=0.6)
    left.set_axisbelow(True)

    right.hlines(0, lower, upper, color=BLUE, linewidth=8, alpha=0.34, zorder=2)
    right.scatter([median], [0], marker="D", s=38, color=BLUE, edgecolor=INK, linewidth=0.55, zorder=3)
    right.scatter([observed], [0], marker="o", s=110, color=ORANGE, edgecolor=INK, linewidth=0.65, zorder=4)
    right.text(
        (lower + upper) / 2,
        -0.27,
        f"Central 95% permutation interval\n{lower:.1f} to {upper:.1f}%",
        ha="center",
        va="top",
    )
    right.annotate(
        f"Observed\n{observed:.1f}%",
        (observed, 0),
        xytext=(0, 18),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontweight="bold",
    )
    right.annotate(
        f"Permutation median\n{median:.1f}%",
        (median, 0),
        xytext=(0, 15),
        textcoords="offset points",
        ha="center",
        va="bottom",
    )
    right.set_xlim(15, 32)
    right.set_xticks([15, 20, 25, 30])
    right.set_ylim(-0.72, 0.68)
    right.set_yticks([])
    right.set_xlabel("Candidates identified repeatedly (%)", labelpad=2)
    right.set_title("Observed proportion exceeded\nthe permutation interval", loc="left", pad=5, fontweight="bold")
    add_panel_label(right, "B")
    box_axes(right)
    right.grid(axis="x", color=GRID, linewidth=0.6)
    right.set_axisbelow(True)

    figure.subplots_adjust(left=0.11, right=0.985, bottom=0.22, top=0.84, wspace=0.42)
    save_main_figure(figure, output_dir, "2", "Repeated candidate identification")


def generate_figure_3(rows: list[dict[str, str]], output_dir: Path) -> None:
    require(len(rows) == 5, f"Figure 3 must describe five studies; found {len(rows)}")
    evaluable = [
        integer(
            row,
            "Accessions or lines assessed (n)",
            context=f"Figure 3 analysis {row['Analysis identifier']}",
        )
        for row in rows
    ]
    none = [
        integer(
            row,
            "Met the study criterion for zero diseases (n)",
            context=f"Figure 3 analysis {row['Analysis identifier']}",
        )
        for row in rows
    ]
    one = [
        integer(
            row,
            "Met the study criterion for one disease (n)",
            context=f"Figure 3 analysis {row['Analysis identifier']}",
        )
        for row in rows
    ]
    multiple = [
        integer(
            row,
            "Met the study criterion for two or more diseases (n)",
            context=f"Figure 3 analysis {row['Analysis identifier']}",
        )
        for row in rows
    ]
    expected = {
        "evaluable": [108, 224, 129, 48, 47],
        "none": [22, 53, 58, 30, 34],
        "one": [61, 95, 58, 17, 13],
        "multiple": [25, 76, 13, 1, 0],
    }
    observed = {"evaluable": evaluable, "none": none, "one": one, "multiple": multiple}
    require(observed == expected, f"Unexpected Figure 3 values: {observed}")
    require(all(n + o + m == total for n, o, m, total in zip(none, one, multiple, evaluable, strict=True)), "Figure 3 study totals do not match denominators")

    figure, axis = plt.subplots(figsize=(7.0, 4.25), facecolor="white")
    y = np.arange(len(rows))
    groups = [
        (none, "Zero diseases", LIGHT_GRAY, INK),
        (one, "One disease", BLUE, "white"),
        (multiple, "Two or more diseases", ORANGE, "white"),
    ]
    left_positions = np.zeros(len(rows), dtype=float)
    for marks_list, label, color, text_color in groups:
        marks = np.asarray(marks_list, dtype=float)
        bars = axis.barh(
            y,
            marks,
            left=left_positions,
            label=label,
            color=color,
            edgecolor="white",
            linewidth=0.8,
            height=0.68,
        )
        for bar, value in zip(bars, marks, strict=True):
            if value == 0:
                continue
            if value >= 8:
                axis.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    str(int(value)),
                    ha="center",
                    va="center",
                    fontweight="bold",
                    color=text_color,
                )
            else:
                axis.annotate(
                    str(int(value)),
                    (bar.get_x() + bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(3, 0),
                    textcoords="offset points",
                    ha="left",
                    va="center",
                    fontweight="bold",
                    color=INK,
                )
        left_positions += marks

    study_labels = {
        "Puerto Rico\n2017–2018": "Puerto Rico\n2017 to 2018",
        "Senegal collection\n2018 workbook": "Senegal collection\n(Cuevas et al. 2018)",
    }
    axis.set_yticks(y, [study_labels.get(row["Study"], row["Study"]) for row in rows])
    axis.invert_yaxis()
    axis.set_xlim(0, 235)
    axis.set_xticks([0, 50, 100, 150, 200])
    axis.set_xlabel("Accessions or lines (n)")
    box_axes(axis)
    axis.grid(axis="x", color=GRID, linewidth=0.65, zorder=0)
    axis.set_axisbelow(True)
    legend = axis.legend(
        loc="lower right",
        title="Number of diseases meeting the study criterion",
        frameon=True,
        framealpha=1,
        facecolor="white",
        edgecolor="#BDBDBD",
        fontsize=9,
        borderpad=0.45,
    )
    legend.get_title().set_fontweight("bold")
    legend.get_frame().set_linewidth(0.65)
    figure.subplots_adjust(left=0.285, right=0.985, bottom=0.16, top=0.97)
    save_main_figure(figure, output_dir, "3", "Disease classifications in five direct comparisons")


def generate_figure_s1(rows: list[dict[str, str]], output_dir: Path) -> None:
    require(len(rows) == 26, f"Figure S1 must describe 26 analyses; found {len(rows)}")
    parsed: list[dict[str, float | int | str]] = []
    for row in rows:
        context = f"Figure S1 analysis {row['Pareto analysis identifier']!r}"
        parsed.append(
            {
                "analysis_identifier": row["Pareto analysis identifier"],
                "assessed_n": integer(row, "Accessions or lines assessed (n)", context=context),
                "pareto_n": integer(row, "Accessions or lines on the Pareto front (n)", context=context),
                "objective_count": integer(row, "Response measures (n)", context=context),
                "disease_count": integer(row, "Diseases examined (n)", context=context),
            }
        )

    # Separate analyses with identical count pairs using deterministic offsets
    # on the natural-log scale. The offsets affect display only; the source CSV
    # retains the reported scientific counts.
    coordinate_groups: dict[tuple[int, int], list[dict[str, float | int | str]]] = {}
    for item in parsed:
        coordinate = (int(item["assessed_n"]), int(item["pareto_n"]))
        coordinate_groups.setdefault(coordinate, []).append(item)
    duplicate_group_sizes = sorted(len(group) for group in coordinate_groups.values() if len(group) > 1)
    require(duplicate_group_sizes == [2, 2, 2], f"Unexpected duplicate Figure S1 coordinates: {duplicate_group_sizes}")
    for group in coordinate_groups.values():
        group.sort(key=lambda item: str(item["analysis_identifier"]))
        offsets = [(0.0, 0.0)] if len(group) == 1 else [(-0.06, 0.06), (0.06, -0.06)]
        require(len(group) == len(offsets), "Figure S1 contains more than two analyses at one coordinate")
        for item, (x_offset, y_offset) in zip(group, offsets, strict=True):
            item["display_x"] = float(item["assessed_n"]) * float(np.exp(x_offset))
            item["display_y"] = float(item["pareto_n"]) * float(np.exp(y_offset))
    require(sum(int(item["pareto_n"]) for item in parsed) == 439, "Figure S1 Pareto total changed")
    require({int(item["objective_count"]) for item in parsed} == {2, 3, 4}, "Figure S1 response-measure counts changed")
    require({int(item["disease_count"]) for item in parsed} == {1, 2, 3}, "Figure S1 disease counts changed")
    require(all(float(item["display_x"]) > 0 and float(item["display_y"]) > 0 for item in parsed), "Figure S1 log-scale coordinates must be positive")

    figure, axis = plt.subplots(figsize=(6.5, 3.8), facecolor="white")
    disease_styles = {1: ("o", GRAY), 2: ("s", BLUE), 3: ("D", ORANGE)}
    size_map = {2: 50, 3: 75, 4: 105}
    for disease_count in (1, 2, 3):
        group = [item for item in parsed if int(item["disease_count"]) == disease_count]
        marker, color = disease_styles[disease_count]
        axis.scatter(
            [float(item["display_x"]) for item in group],
            [float(item["display_y"]) for item in group],
            s=[size_map[int(item["objective_count"])] for item in group],
            marker=marker,
            color=color,
            edgecolor=INK,
            linewidth=0.65,
            alpha=0.92,
            zorder=3,
        )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("Accessions or lines assessed (n; log scale)")
    axis.set_ylabel("Accessions or lines on the Pareto front (n; log scale)")
    axis.set_xlim(10, 400)
    axis.set_ylim(0.7, 300)
    axis.set_xticks([10, 20, 50, 100, 200, 400], labels=["10", "20", "50", "100", "200", "400"])
    axis.set_yticks([1, 2, 5, 10, 20, 50, 100, 200], labels=["1", "2", "5", "10", "20", "50", "100", "200"])
    axis.minorticks_off()
    style_supplement_axis(axis)

    disease_handles = [
        Line2D(
            [0],
            [0],
            marker=disease_styles[count][0],
            linestyle="",
            markersize=6.5,
            markerfacecolor=disease_styles[count][1],
            markeredgecolor=INK,
            label=f"{count} disease" + ("" if count == 1 else "s"),
        )
        for count in (1, 2, 3)
    ]
    response_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markersize={2: 5.8, 3: 7.2, 4: 8.5}[count],
            markerfacecolor="white",
            markeredgecolor=INK,
            label=f"{count} measures",
        )
        for count in (2, 3, 4)
    ]
    first = axis.legend(
        handles=disease_handles,
        title="Diseases examined",
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        frameon=True,
        framealpha=1,
        facecolor="white",
        edgecolor="#BDBDBD",
        fontsize=9,
        title_fontsize=9,
        borderpad=0.45,
        handletextpad=0.45,
    )
    first.get_title().set_fontweight("bold")
    first.get_frame().set_linewidth(0.65)
    axis.add_artist(first)
    second = axis.legend(
        handles=response_handles,
        title="Response measures",
        loc="lower left",
        bbox_to_anchor=(1.02, 0.0),
        frameon=True,
        framealpha=1,
        facecolor="white",
        edgecolor="#BDBDBD",
        fontsize=9,
        title_fontsize=9,
        borderpad=0.45,
        handletextpad=0.45,
    )
    second.get_title().set_fontweight("bold")
    second.get_frame().set_linewidth(0.65)
    figure.subplots_adjust(left=0.14, right=0.72, bottom=0.17, top=0.97)

    creator = f"Matplotlib {matplotlib.__version__}"
    figure.savefig(
        output_dir / "Figure_S1_artwork.pdf",
        format="pdf",
        facecolor="white",
        metadata={"Title": "Pareto fronts in 26 sorghum disease-response analyses", "Creator": creator},
    )
    figure.savefig(
        output_dir / "Figure_S1.svg",
        format="svg",
        facecolor="white",
        metadata={"Title": "Pareto fronts in 26 sorghum disease-response analyses", "Creator": creator, "Date": None},
    )
    figure.savefig(
        output_dir / "Figure_S1_600dpi.png",
        format="png",
        dpi=600,
        facecolor="white",
        metadata={"Title": "Pareto fronts in 26 sorghum disease-response analyses", "Software": creator},
    )
    plt.close(figure)

    artwork = plt.imread(output_dir / "Figure_S1_600dpi.png")
    page = plt.figure(figsize=(8.5, 11.0), facecolor="white")
    page.text(
        1.0 / 8.5,
        0.91,
        "Supplementary Figure S1",
        ha="left",
        va="top",
        fontsize=12,
        fontweight="bold",
        fontfamily=FONT_NAME,
        color=INK,
    )
    page_axis = page.add_axes([1.0 / 8.5, 0.49, 6.5 / 8.5, 3.8 / 11.0])
    page_axis.imshow(artwork)
    page_axis.axis("off")
    page.text(
        1.0 / 8.5,
        0.42,
        textwrap.fill(FIGURE_S1_CAPTION, width=84),
        ha="left",
        va="top",
        fontsize=12,
        fontfamily=FONT_NAME,
        linespacing=2.0,
        color=INK,
    )
    page.savefig(
        output_dir / "Figure_S1.pdf",
        format="pdf",
        dpi=300,
        metadata={
            "Title": "Supplementary Figure S1",
            "Subject": "Pareto fronts in 26 sorghum disease-response analyses",
            "Author": "James Liu; Louis K. Prom; Ezekiel Ahn",
            "Creator": creator,
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(page)


def verify_outputs(output_dir: Path) -> None:
    expected_pixels = {
        "Figure_1.tif": (4200, 4620),
        "Figure_2.tif": (4200, 2550),
        "Figure_3.tif": (4200, 2550),
        "Figure_S1_600dpi.png": (3900, 2280),
    }
    for filename, expected_size in expected_pixels.items():
        path = output_dir / filename
        require(path.is_file(), f"Expected output was not created: {path}")
        with Image.open(path) as image:
            require(image.size == expected_size, f"{filename} has size {image.size}; expected {expected_size}")
            dpi = image.info.get("dpi", (0, 0))
            require(all(abs(float(value) - 600) < 1 for value in dpi), f"{filename} does not report 600 dpi: {dpi}")
            if filename.endswith(".tif"):
                require(image.mode == "RGB", f"{filename} must be RGB; found {image.mode}")
                compression = image.tag_v2.get(259)
                require(compression == 5, f"{filename} must use LZW compression; TIFF tag 259 is {compression}")
    for filename in ("Figure_1.pdf", "Figure_2.pdf", "Figure_3.pdf", "Figure_S1.pdf", "Figure_S1_artwork.pdf", "Figure_S1.svg"):
        require((output_dir / filename).is_file(), f"Expected output was not created: {output_dir / filename}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate current v23 manuscript Figures 1 to 3 and supplementary Figure S1 from four supplied CSV files."
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="Directory containing the CSV files used to draw Figures 1 to 3 and Figure S1.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory in which figure files will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    require(data_dir.is_dir(), f"Data directory does not exist: {data_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    configure_matplotlib()
    rows = {
        number_text: read_csv_rows(data_dir / filename, EXPECTED_COLUMNS[number_text])
        for number_text, filename in INPUT_FILES.items()
    }
    generate_figure_1(rows["1"], output_dir)
    generate_figure_2(rows["2"], output_dir)
    generate_figure_3(rows["3"], output_dir)
    generate_figure_s1(rows["S1"], output_dir)
    verify_outputs(output_dir)

    written = [
        "Figure_1.tif",
        "Figure_1.pdf",
        "Figure_2.tif",
        "Figure_2.pdf",
        "Figure_3.tif",
        "Figure_3.pdf",
        "Figure_S1.pdf",
        "Figure_S1_artwork.pdf",
        "Figure_S1.svg",
        "Figure_S1_600dpi.png",
    ]
    print("Generated and verified:")
    for filename in written:
        print(f"  {output_dir / filename}")


if __name__ == "__main__":
    main()
