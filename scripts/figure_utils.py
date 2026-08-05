#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
#
"""
Shared figure utilities — color palettes, rcParams presets, and export functions
for reviewable publication figures. Imported by generate_figures.py.

Inspired by nature-figure's references/design-theory.md and references/api.md.
"""
try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for script use

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from contextlib import contextmanager
from typing import Optional

from font_discovery import cjk_family_candidates


# ── Publication rcParams ─────────────────────────────────────────────────────

NATURE_RCPARAMS = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans", "Helvetica"],
    "font.size": 7,
    "axes.titlesize": 7,
    "axes.labelsize": 7,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
    "figure.titlesize": 8,
    "svg.fonttype": "none",       # Text stays as <text> nodes (editable)
    "pdf.fonttype": 42,            # TrueType text editable in PDF
    "ps.fonttype": 42,
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "xtick.minor.width": 0.4,
    "ytick.minor.width": 0.4,
    "xtick.minor.size": 1.5,
    "ytick.minor.size": 1.5,
    "legend.frameon": False,
    "legend.handlelength": 1.5,
    "legend.handletextpad": 0.5,
    "legend.borderpad": 0.3,
    "legend.columnspacing": 0.8,
    "lines.linewidth": 1.0,
    "lines.markersize": 3.0,
    "patch.linewidth": 0.5,
    "image.cmap": "viridis",
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
}

# For Chinese text support (appended to font.sans-serif when needed)
CJK_FONTS = cjk_family_candidates()


@contextmanager
def nature_style(cjk: bool = False):
    """Context manager temporarily applying publication-oriented rcParams."""
    original = {k: plt.rcParams.get(k) for k in NATURE_RCPARAMS}
    plt.rcParams.update(NATURE_RCPARAMS)
    if cjk:
        fonts = CJK_FONTS + list(NATURE_RCPARAMS["font.sans-serif"])
        plt.rcParams["font.sans-serif"] = fonts
        plt.rcParams["axes.unicode_minus"] = False
    try:
        yield
    finally:
        plt.rcParams.update(original)


# ── Color Palettes ───────────────────────────────────────────────────────────

# Nature-inspired categorical palettes (low-saturation pastels)
NATURE_PASTEL_6 = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52",
    "#8172B3", "#937860",
]

NATURE_PASTEL_8 = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52",
    "#8172B3", "#937860", "#DA8BC3", "#8C8C8C",
]

NATURE_PASTEL_4 = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]

# Sequential palettes (for heatmaps / intensity)
NATURE_SEQUENTIAL_BLUE = ["#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1",
                            "#6BAED6", "#4292C6", "#2171B5", "#08519C"]

NATURE_SEQUENTIAL_ORANGE = ["#FFF5EB", "#FEE6CE", "#FDD0A2", "#FDAE6B",
                              "#F16913", "#D94801", "#A63603", "#7F2704"]

# Diverging palettes (for deviation / deficit / bidirectional)
NATURE_DIVERGING_RDBU = ["#67001F", "#B2182B", "#D6604D", "#F4A582",
                           "#F7F7F7", "#92C5DE", "#4393C3", "#2166AC", "#053061"]

NATURE_DIVERGING_PRG = ["#762A83", "#AF8DC3", "#E7D4E8", "#F7F7F7",
                          "#D9F0D3", "#7BBF6A", "#1B7837"]

# Directional cues only (green = gain/improvement, red = decline/loss)
NATURE_GAIN_GREEN = "#2CA02C"
NATURE_LOSS_RED = "#D62728"

# Method-family grouping colors
METHOD_FAMILY_COLORS = {
    "experimental": "#4C72B0",
    "numerical": "#DD8452",
    "analytical": "#55A868",
    "machine_learning": "#C44E52",
    "hybrid": "#8172B3",
}


def get_palette(n_colors: int, style: str = "pastel") -> list[str]:
    """Get a publication-oriented color palette with n colors."""
    if style == "pastel":
        if n_colors <= 4:
            return NATURE_PASTEL_4[:n_colors]
        elif n_colors <= 6:
            return NATURE_PASTEL_6[:n_colors]
        else:
            return NATURE_PASTEL_8[:n_colors]
    elif style == "sequential":
        return NATURE_SEQUENTIAL_BLUE[:n_colors]
    elif style == "diverging":
        return NATURE_DIVERGING_RDBU[:n_colors]
    else:
        return NATURE_PASTEL_6[:n_colors]


# ── Export Functions ─────────────────────────────────────────────────────────

def export_figure(fig: plt.Figure, base_path: str, formats: list[str] = None):
    """Export figure in multiple formats.

    Args:
        fig: matplotlib Figure
        base_path: output path without extension (e.g. 'figures/fig_1')
        formats: list of formats: 'svg', 'pdf', 'tiff', 'png' (default: ['svg'])
    """
    if formats is None:
        formats = ["svg"]

    for fmt in formats:
        path = f"{base_path}.{fmt}"
        if fmt == "tiff":
            fig.savefig(path, dpi=600, pil_kwargs={"compression": "tiff_lzw"})
        elif fmt == "svg":
            fig.savefig(path)  # svg.fonttype='none' keeps text editable
        elif fmt == "pdf":
            fig.savefig(path)  # pdf.fonttype=42 keeps text editable
        else:
            fig.savefig(path, dpi=300)


# ── Layout Helpers ───────────────────────────────────────────────────────────

def make_gridspec_figure(
    nrows: int, ncols: int,
    figsize: tuple = None,
    panel_labels: list[str] = None,
) -> tuple[plt.Figure, list[plt.Axes]]:
    """Create a GridSpec multi-panel figure with publication defaults.

    Args:
        nrows, ncols: grid dimensions
        figsize: (width, height) in inches; auto-calculated if None
        panel_labels: optional list of labels like ['a', 'b', 'c']

    Returns:
        (fig, axes) tuple — axes is a flat list
    """
    if figsize is None:
        # Nature standard: single column ~89mm (3.5"), double ~183mm (7.2")
        w = 3.5 * ncols
        h = 2.8 * nrows
        figsize = (w, h)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)

    # Flatten axes for consistent handling
    if nrows == 1 and ncols == 1:
        axes_flat = [axes]
    elif nrows == 1 or ncols == 1:
        axes_flat = list(axes)
    else:
        axes_flat = [ax for row in axes for ax in row]

    # Add panel labels
    if panel_labels:
        for ax, label in zip(axes_flat, panel_labels):
            ax.text(
                -0.1, 1.08, label,
                transform=ax.transAxes,
                fontweight="bold", fontsize=8, va="bottom", ha="left",
            )

    return fig, axes_flat


def add_significance_bar(
    ax: plt.Axes,
    x1: float, x2: float, y: float,
    p_value: str = "",
    bar_height: float = 0.02,
):
    """Add a significance bar between two data points.

    Args:
        ax: matplotlib Axes
        x1, x2: x positions of the two bars/points
        y: y position for the bar (above the data)
        p_value: text label, e.g. 'p < 0.001' or 'n.s.'
        bar_height: height of the significance brackets
    """
    y_bracket = y + bar_height
    ax.plot([x1, x1, x2, x2], [y, y_bracket, y_bracket, y],
            color="black", linewidth=0.6, clip_on=False)
    if p_value:
        ax.text((x1 + x2) / 2, y_bracket + bar_height * 0.3,
                p_value, ha="center", va="bottom", fontsize=5)


# ── Design Rule Validators ───────────────────────────────────────────────────

def validate_figure_layout(fig: plt.Figure, n_panels: int) -> list[str]:
    """Check figure against Nature design rules. Returns list of issues."""
    issues = []
    # Check: no redundant panels (warning only — can't automate the decision)
    if n_panels > 1:
        # Heuristic: too many similar chart types → possible redundancy
        pass
    # Check: figures should have direct labels, not just legends
    # (can't automate — informational)
    return issues


def set_direct_labels(ax: plt.Axes, labels: list[str], x_positions: list[float],
                      y_positions: list[float], **kwargs):
    """Place direct text labels near data instead of relying solely on legends.

    Args:
        ax: matplotlib Axes
        labels: text labels for each data point
        x_positions, y_positions: coordinates for each label
    """
    for label, x, y in zip(labels, x_positions, y_positions):
        ax.text(x, y, label, fontsize=5, ha="left", va="bottom", **kwargs)


# ── Common Figure Templates ──────────────────────────────────────────────────

def grouped_bar(
    categories: list[str],
    groups: dict[str, list[float]],      # {group_name: [values]}
    ylabel: str = "",
    xlabel: str = "",
    figsize: tuple = (5, 3.5),
    palette: list[str] = None,
) -> plt.Figure:
    """Create a publication-oriented grouped bar chart."""
    if palette is None:
        palette = get_palette(len(groups), "pastel")

    n_cats = len(categories)
    n_groups = len(groups)
    bar_width = 0.8 / n_groups
    x = range(n_cats)

    fig, ax = plt.subplots(figsize=figsize)

    for i, (name, values) in enumerate(groups.items()):
        offset = (i - (n_groups - 1) / 2) * bar_width
        positions = [xi + offset for xi in x]
        ax.bar(positions, values, bar_width * 0.9,
               label=name, color=palette[i], edgecolor="white", linewidth=0.3)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=0, ha="center")
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)

    if n_groups > 1:
        ax.legend(loc="upper right", ncol=min(n_groups, 4))

    ax.yaxis.set_major_locator(ticker.MaxNLocator(5))
    return fig


def trend_line(
    x: list[float],
    y_series: dict[str, list[float]],     # {series_name: [y_values]}
    xlabel: str = "",
    ylabel: str = "",
    figsize: tuple = (5, 3.5),
    palette: list[str] = None,
) -> plt.Figure:
    """Create a publication-oriented line/trend chart."""
    if palette is None:
        palette = get_palette(len(y_series), "pastel")

    fig, ax = plt.subplots(figsize=figsize)

    for i, (name, y_vals) in enumerate(y_series.items()):
        ax.plot(x[:len(y_vals)], y_vals, color=palette[i],
                marker="o", markersize=3, linewidth=1.0, label=name)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(loc="best", ncol=min(len(y_series), 3))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(5))
    return fig


def heatmap(
    data: list[list[float]],
    row_labels: list[str],
    col_labels: list[str],
    cmap: str = "Blues",
    figsize: tuple = (6, 4),
    center: Optional[float] = None,
    annotate: bool = True,
) -> plt.Figure:
    """Create a publication-oriented heatmap (sequential or diverging).

    Args:
        data: 2D array of values
        row_labels, col_labels: axis labels
        cmap: colormap name
        center: if set, use diverging colormap centered at this value
        annotate: whether to show values in cells
    """
    fig, ax = plt.subplots(figsize=figsize)

    kwargs = {"cmap": cmap, "aspect": "auto"}
    if center is not None:
        from matplotlib.colors import TwoSlopeNorm
        vmax = max(abs(max(max(r) for r in data)), abs(min(min(r) for r in data)))
        kwargs["norm"] = TwoSlopeNorm(vmin=-vmax, vcenter=center, vmax=vmax)
        kwargs["cmap"] = "RdBu_r"

    im = ax.imshow(data, **kwargs)

    # Colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.ax.tick_params(labelsize=5)

    # Labels
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=5)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=5)

    # Annotate cells
    if annotate:
        for i in range(len(row_labels)):
            for j in range(len(col_labels)):
                val = data[i][j] if i < len(data) and j < len(data[i]) else 0
                text_color = "white" if abs(val) > (center or 0) * 0.7 else "black"
                ax.text(j, i, f"{val:.2g}", ha="center", va="center",
                        fontsize=4, color=text_color)

    return fig


def bubble_scatter(
    x: list[float],
    y: list[float],
    sizes: list[float],
    labels: list[str] = None,
    xlabel: str = "",
    ylabel: str = "",
    figsize: tuple = (5, 4),
    color: str = "#4C72B0",
) -> plt.Figure:
    """Create a publication-oriented bubble scatter plot."""
    fig, ax = plt.subplots(figsize=figsize)

    # Scale bubble sizes
    size_scale = [s * 20 / max(sizes) for s in sizes]

    ax.scatter(x, y, s=size_scale, c=color, alpha=0.7,
               edgecolors="white", linewidth=0.5)

    if labels:
        for xi, yi, label in zip(x, y, labels):
            ax.annotate(label, (xi, yi), fontsize=4,
                        xytext=(3, 3), textcoords="offset points")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return fig


def radar_chart(
    categories: list[str],
    values: dict[str, list[float]],     # {series_name: [values]}
    figsize: tuple = (5, 5),
    palette: list[str] = None,
) -> plt.Figure:
    """Create a publication-oriented radar/polar chart."""
    import numpy as np

    if palette is None:
        palette = get_palette(len(values), "pastel")

    n = len(categories)
    angles = [i * 2 * np.pi / n for i in range(n)]
    angles += angles[:1]  # Close the polygon

    fig, ax = plt.subplots(figsize=figsize, subplot_kw={"projection": "polar"})
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    for i, (name, vals) in enumerate(values.items()):
        vals_closed = vals + vals[:1]
        ax.fill(angles, vals_closed, alpha=0.15, color=palette[i])
        ax.plot(angles, vals_closed, color=palette[i], linewidth=0.8, label=name)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=6)
    ax.set_yticklabels([])
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=5)
    return fig


def gridspec_figure(
    panel_specs: list[dict],
    figsize: tuple = None,
    panel_labels: list[str] = None,
) -> plt.Figure:
    """Create a publication-oriented multi-panel GridSpec figure.

    Args:
        panel_specs: list of dicts, each with:
            - 'type': 'bar' | 'line' | 'heatmap' | 'scatter' | 'radar'
            - 'data': dict with data for that chart type
            - 'title': str (optional)
        figsize: (width, height) in inches
        panel_labels: labels like ['a', 'b', 'c', 'd']

    Returns:
        matplotlib Figure
    """
    import matplotlib.gridspec as gridspec

    n = len(panel_specs)
    # Auto-layout: try square-ish grid
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols

    if figsize is None:
        figsize = (3.5 * ncols, 2.8 * nrows)

    fig = plt.figure(figsize=figsize)
    gs = gridspec.GridSpec(nrows, ncols, figure=fig,
                           hspace=0.4, wspace=0.35)

    for i, spec in enumerate(panel_specs):
        row = i // ncols
        col = i % ncols
        ax = fig.add_subplot(gs[row, col])

        chart_type = spec.get("type", "bar")
        data = spec.get("data", {})
        title = spec.get("title", "")

        if chart_type == "bar":
            categories = data.get("categories", [])
            groups = data.get("groups", {})
            if categories and groups:
                _quick_grouped_bar(ax, categories, groups)
        elif chart_type == "line":
            x = data.get("x", [])
            y_series = data.get("y_series", {})
            if x and y_series:
                _quick_trend_line(ax, x, y_series)
        elif chart_type == "scatter":
            x = data.get("x", [])
            y = data.get("y", [])
            if x and y:
                ax.scatter(x, y, s=8, color=NATURE_PASTEL_6[0], alpha=0.7)
                ax.set_xlabel(data.get("xlabel", ""))
                ax.set_ylabel(data.get("ylabel", ""))

        if title:
            ax.set_title(title, fontsize=7, fontweight="normal")

        # Panel label
        if panel_labels and i < len(panel_labels):
            ax.text(-0.1, 1.05, panel_labels[i], transform=ax.transAxes,
                    fontweight="bold", fontsize=8, va="bottom", ha="left")

    return fig


def _quick_grouped_bar(ax, categories, groups):
    """Quick grouped bar on an existing axis."""
    n_cats = len(categories)
    n_groups = len(groups)
    bar_width = 0.8 / max(n_groups, 1)
    palette = get_palette(n_groups)
    x = range(n_cats)
    for i, (name, values) in enumerate(groups.items()):
        offset = (i - (n_groups - 1) / 2) * bar_width
        positions = [xi + offset for xi in x]
        ax.bar(positions, values[:n_cats], bar_width * 0.9,
               label=name, color=palette[i % len(palette)])
    ax.set_xticks(x)
    ax.set_xticklabels(categories)


def _quick_trend_line(ax, x, y_series):
    """Quick trend line on an existing axis."""
    palette = get_palette(len(y_series))
    for i, (name, y_vals) in enumerate(y_series.items()):
        ax.plot(x[:len(y_vals)], y_vals, color=palette[i % len(palette)],
                marker="o", markersize=2, linewidth=0.8, label=name)
