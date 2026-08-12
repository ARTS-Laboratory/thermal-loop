#!/usr/bin/env python3
# =============================================================================
#  finalize_plot.py  --  CORE^2S poster figure finalizer
# =============================================================================
#
#  WHAT THIS DOES
#  --------------
#  Turns a logged run into ONE print-ready figure for a poster:
#
#      top panel     temperature vs time
#      bottom panel  heat exchanger flow (left axis) + rod power (right axis)
#
#  Both panels share an x-axis, so a vertical "event" line drawn at t = 86 min
#  cuts through both and the reader sees cause and effect lined up.
#
#
#  HOW TO USE IT  (read this part)
#  -------------------------------
#  STEP 1.  Put this file anywhere you like. It does not need to live in the
#           data folder.
#
#  STEP 2.  Point it at ONE run folder -- the folder that holds the CSVs for a
#           single test, e.g.
#
#               .../thermal-loop/resources/v0.1.1/data/001/
#
#           Run:
#
#               python finalize_plot.py .../data/001
#
#  STEP 3.  The FIRST run does not make a figure. It scans the CSVs it finds,
#           then writes a starter file:
#
#               <run folder>/annotations.json
#
#           That file is where you describe the run. It is pre-filled with the
#           real column names found in your CSVs, so you are editing, not
#           authoring from scratch.
#
#  STEP 4.  Open annotations.json and fill it in. See "WHAT GOES IN
#           annotations.json" below for every field.
#
#  STEP 5.  Run the same command again. Now it builds the figure and writes:
#
#               <run folder>/poster/<output_name>.pdf     <- use this for print
#               <run folder>/poster/<output_name>.png     <- use this to preview
#
#  STEP 6.  Look at the PNG, edit annotations.json, re-run. Repeat until happy.
#           Re-running always overwrites the figures and never touches your
#           annotations.json or your data.
#
#  Useful flags:
#      --reset       overwrite annotations.json with a fresh starter file
#      --show        pop the figure up in a window instead of only saving
#
#
#  WHAT GOES IN annotations.json
#  -----------------------------
#  "output_name"   filename stem for the saved figure.
#
#  "title"         headline above the figure. Say what the run SHOWS, not what
#                  it is: "Loop response to reduced heat exchanger flow" beats
#                  "Run 001 temperature data".
#  "subtitle"      smaller line under it. Good place for conditions:
#                  "Rod 2.5 V, 1.2 kW - secondary flow stepped 1.8 -> 1.0 GPM".
#
#  "files"         which CSV holds what. Each entry has the filename and the
#                  name of its time column. Files are read independently, so
#                  they do NOT need a common time base or the same row count.
#                     "temperature": {"path": "temperature.csv",
#                                     "time_column": "time_s"}
#                     "flow":        {"path": "flow.csv",
#                                     "time_column": "time_s"}
#                  Set "flow" to null if that run has no flow file.
#
#  "time"          "units": "min" or "s" -- what the x-axis shows.
#                  "zero_at": seconds into the log to call t = 0. Use this to
#                  chop off warm-up you do not want on the poster.
#                  "xlim": [start, end] in the units above, or null for auto.
#
#  "temperature"   How to draw the top panel. THIS IS THE IMPORTANT ONE.
#                    "band": list of columns to draw as ONE shaded min/max band
#                            with a mean line through it. Put the primary-loop
#                            thermocouples here. Eight separate wiggly lines is
#                            the single most common way to wreck a poster
#                            figure; a band says "these all track together"
#                            in one visual element.
#                    "band_label": legend text for that band.
#                    "lines": columns to draw as their own named curves, as
#                            {"column": "label"} pairs. Put the ones that tell
#                            the story here -- secondary in, secondary out.
#                    "ylim": [low, high] or null for auto.
#
#  "flow"          Bottom panel, left axis.
#                    "column": which column in the flow file to plot.
#                    "label", "ylim".
#
#  "power"         Bottom panel, right axis. Drawn as a STEP line, because rod
#                  power is set per test point, not logged continuously.
#                  A list of {"t": <time>, "kw": <kilowatts>} entries. Each one
#                  means "from this time onward, power was this". Example:
#                     [{"t": 0, "kw": 1.21}, {"t": 120, "kw": 1.85}]
#                  Leave the list empty to hide the power axis entirely.
#
#  "events"        Vertical lines through BOTH panels. Each entry:
#                     {"t": 86, "kind": "flow", "label": "HX flow 1.8 -> 1.0 GPM"}
#                  "kind" picks the color and dash pattern from "style" below,
#                  so every figure you make uses the same visual language.
#                  Built-in kinds: "flow", "power", "valve", "other".
#                  Labels auto-stagger vertically so they do not collide.
#
#  "spans"         Shaded time regions, e.g. a steady-state window:
#                     {"t0": 20, "t1": 85, "label": "Steady state"}
#
#  "callouts"      Pinned text with a leader line, for calling out a specific
#                  value on the temperature panel:
#                     {"t": 85, "y": 34.3, "text": "34.3 C peak",
#                      "dx": 12, "dy": 20}
#                  dx/dy nudge the label away from the point, in points.
#
#  "figure"        "width_in" / "height_in": SET THESE TO THE REAL PRINTED SIZE
#                  the figure will occupy on the poster, in inches. If it goes
#                  in a 13-inch-wide column, put 13. Do this and every font
#                  size below is a true printed point size. If you instead
#                  build a small figure and scale it up in PowerPoint, your
#                  14 pt labels silently become 7 pt and nobody can read them.
#                  "dpi": only affects the PNG preview; the PDF is vector.
#
#  "fonts"         Point sizes for title, subtitle, axis labels, ticks,
#                  legend, and annotations. Poster minimum is usually 24 pt for
#                  body text; figure labels can run a bit smaller, but do not
#                  go below about 14 pt for anything a judge needs to read.
#
#  "style"         Colors. "palette" holds the line colors; "event_kinds" maps
#                  each event kind to a color and dash pattern. The defaults
#                  are pulled toward the USC template accents so the figure
#                  looks like it belongs on the poster instead of looking like
#                  stock matplotlib.
#
#
#  NOTES
#  -----
#  * Nothing here modifies your CSVs or your analyze.py output. This script
#    only reads data and only writes into <run folder>/poster/.
#  * Use the PDF for the poster. It is vector, so it stays sharp at any size,
#    and fonts are embedded (fonttype 42) so the print shop cannot substitute
#    them.
#  * If a column name in annotations.json does not exist in the CSV, the script
#    tells you which one and lists what IS in the file, rather than crashing
#    with a KeyError.
# =============================================================================

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import AutoMinorLocator  # noqa: E402

# Embed real fonts in vector output instead of drawing text as outlines.
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["svg.fonttype"] = "none"


# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------

DEFAULT_STYLE = {
    "palette": {
        "band_fill": "#9FB6C9",
        "band_line": "#1E3D4F",
        "line_1": "#C8102E",
        "line_2": "#2E7D8F",
        "line_3": "#8A8B22",
        "flow": "#2E7D8F",
        "power": "#C8102E",
        "span": "#E8E4D8",
        "grid": "#D6D2C8",
        "text": "#1B1B1B",
    },
    "event_kinds": {
        "flow": {"color": "#2E7D8F", "dash": [6, 4]},
        "power": {"color": "#C8102E", "dash": [2, 3]},
        "valve": {"color": "#8A8B22", "dash": [10, 4, 2, 4]},
        "other": {"color": "#5A5A5A", "dash": [4, 4]},
    },
}

DEFAULT_FONTS = {
    "title": 22,
    "subtitle": 16,
    "axis_label": 17,
    "tick": 14,
    "legend": 14,
    "annotation": 13,
}

TIME_HINTS = ["time_s", "elapsed_s", "elapsed", "timestamp", "time", "t_s", "t"]
TEMP_HINTS = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"]
FLOW_HINTS = ["flow", "gpm"]


# -----------------------------------------------------------------------------
# Discovery helpers -- used only to build the starter annotations.json
# -----------------------------------------------------------------------------

def _pick_time_column(columns):
    lowered = {c.lower(): c for c in columns}
    for hint in TIME_HINTS:
        if hint in lowered:
            return lowered[hint]
    for c in columns:
        if "time" in c.lower():
            return c
    return columns[0] if len(columns) else None


def _find_csv(run_dir, *keywords):
    """Return the first CSV in run_dir whose name contains any keyword."""
    for path in sorted(run_dir.glob("*.csv")):
        name = path.name.lower()
        if any(k in name for k in keywords):
            return path
    return None


def _temperature_columns(columns):
    out = [c for c in columns if c.lower() in TEMP_HINTS]
    if out:
        return out
    return [c for c in columns if c.lower().startswith("t") and c.lower() != "time"]


def build_starter_config(run_dir):
    """Inspect the CSVs in run_dir and return a filled-in starter config."""
    temp_csv = _find_csv(run_dir, "temp") or _find_csv(run_dir, "data")
    flow_csv = _find_csv(run_dir, "flow")

    temp_cols, temp_time = [], "time_s"
    if temp_csv is not None:
        head = pd.read_csv(temp_csv, nrows=5)
        temp_time = _pick_time_column(list(head.columns)) or "time_s"
        temp_cols = _temperature_columns([c for c in head.columns if c != temp_time])

    flow_col, flow_time = None, "time_s"
    if flow_csv is not None:
        head = pd.read_csv(flow_csv, nrows=5)
        flow_time = _pick_time_column(list(head.columns)) or "time_s"
        for c in head.columns:
            if c != flow_time and any(h in c.lower() for h in FLOW_HINTS):
                flow_col = c
                break

    # Put the last two temperature channels on their own curves as a starting
    # guess; the heat exchanger channels are usually the interesting ones.
    band = temp_cols[:-2] if len(temp_cols) > 2 else temp_cols
    named = {c: c for c in temp_cols[len(band):]}

    return {
        "_README": "Field-by-field docs are in the header of finalize_plot.py.",
        "output_name": f"{run_dir.name}_temperature",
        "title": "TITLE: what this run shows",
        "subtitle": "Conditions: rod voltage, power, secondary flow",
        "files": {
            "temperature": {
                "path": temp_csv.name if temp_csv else "temperature.csv",
                "time_column": temp_time,
            },
            "flow": (
                {"path": flow_csv.name, "time_column": flow_time}
                if flow_csv
                else None
            ),
        },
        "time": {"units": "min", "zero_at": 0.0, "xlim": None},
        "temperature": {
            "band": band,
            "band_label": "Primary loop (min-max)",
            "lines": named,
            "ylim": None,
            "label": "Temperature (\u00b0C)",
        },
        "flow": {
            "column": flow_col,
            "label": "HX flow (GPM)",
            "ylim": None,
        },
        "power": [],
        "events": [],
        "spans": [],
        "callouts": [],
        "figure": {"width_in": 13.0, "height_in": 7.5, "dpi": 200},
        "fonts": dict(DEFAULT_FONTS),
        "style": json.loads(json.dumps(DEFAULT_STYLE)),
    }


# -----------------------------------------------------------------------------
# Loading
# -----------------------------------------------------------------------------

def _fail(msg):
    print(f"\n[finalize_plot] {msg}\n", file=sys.stderr)
    sys.exit(1)


def load_table(run_dir, spec, cfg, what):
    """Load one CSV and return (dataframe, time_vector_in_display_units)."""
    if not spec:
        return None, None
    path = run_dir / spec["path"]
    if not path.exists():
        _fail(f"{what} file not found: {path}")

    df = pd.read_csv(path)
    tcol = spec.get("time_column")
    if tcol not in df.columns:
        _fail(
            f"time column '{tcol}' is not in {path.name}.\n"
            f"           Columns present: {list(df.columns)}"
        )

    raw = df[tcol]
    if np.issubdtype(raw.dtype, np.number):
        seconds = raw.to_numpy(dtype=float)
    else:
        parsed = pd.to_datetime(raw, errors="coerce")
        if parsed.isna().all():
            _fail(f"could not interpret '{tcol}' in {path.name} as time.")
        seconds = (parsed - parsed.iloc[0]).dt.total_seconds().to_numpy()

    seconds = seconds - seconds[0] - float(cfg["time"].get("zero_at", 0.0))
    t = seconds / 60.0 if cfg["time"].get("units", "min") == "min" else seconds
    return df, t


def require_columns(df, wanted, source):
    missing = [c for c in wanted if c not in df.columns]
    if missing:
        _fail(
            f"these columns are not in {source}: {missing}\n"
            f"           Columns present: {list(df.columns)}"
        )


# -----------------------------------------------------------------------------
# Plotting
# -----------------------------------------------------------------------------

def draw(cfg, temp_df, temp_t, flow_df, flow_t):
    style = cfg["style"]
    pal = style["palette"]
    fonts = cfg["fonts"]
    fig_cfg = cfg["figure"]

    power_steps = cfg.get("power") or []
    has_bottom = (flow_df is not None and cfg["flow"].get("column")) or power_steps

    if has_bottom:
        fig, (ax_t, ax_b) = plt.subplots(
            2, 1, sharex=True, layout="constrained",
            figsize=(fig_cfg["width_in"], fig_cfg["height_in"]),
            gridspec_kw={"height_ratios": [3, 1.15]},
        )
        axes = [ax_t, ax_b]
    else:
        fig, ax_t = plt.subplots(
            layout="constrained",
            figsize=(fig_cfg["width_in"], fig_cfg["height_in"])
        )
        ax_b, axes = None, [ax_t]

    # --- shaded spans (drawn first so everything else sits on top) ----------
    for span in cfg.get("spans", []):
        for ax in axes:
            ax.axvspan(span["t0"], span["t1"], color=pal["span"], zorder=0)
        if span.get("label"):
            ax_t.text(
                (span["t0"] + span["t1"]) / 2, 0.965, span["label"],
                transform=ax_t.get_xaxis_transform(),
                ha="center", va="top", fontsize=fonts["annotation"],
                color=pal["text"], style="italic", zorder=3,
            )

    # --- temperature panel --------------------------------------------------
    tcfg = cfg["temperature"]
    band_cols = tcfg.get("band") or []
    if band_cols:
        require_columns(temp_df, band_cols, cfg["files"]["temperature"]["path"])
        block = temp_df[band_cols].to_numpy(dtype=float)
        lo, hi, mean = block.min(axis=1), block.max(axis=1), block.mean(axis=1)
        ax_t.fill_between(
            temp_t, lo, hi, color=pal["band_fill"], alpha=0.55, linewidth=0,
            label=tcfg.get("band_label", "Band"), zorder=2,
        )
        ax_t.plot(temp_t, mean, color=pal["band_line"], linewidth=2.4, zorder=3)

    line_colors = [pal["line_1"], pal["line_2"], pal["line_3"]]
    named = tcfg.get("lines") or {}
    require_columns(temp_df, list(named.keys()), cfg["files"]["temperature"]["path"])
    for i, (col, label) in enumerate(named.items()):
        ax_t.plot(
            temp_t, temp_df[col].to_numpy(dtype=float),
            color=line_colors[i % len(line_colors)],
            linewidth=2.4, label=label, zorder=4,
        )

    ax_t.set_ylabel(tcfg.get("label", "Temperature (\u00b0C)"),
                    fontsize=fonts["axis_label"], color=pal["text"])
    if tcfg.get("ylim"):
        ax_t.set_ylim(tcfg["ylim"])

    # --- bottom panel -------------------------------------------------------
    if ax_b is not None:
        fcfg = cfg["flow"]
        if flow_df is not None and fcfg.get("column"):
            require_columns(flow_df, [fcfg["column"]], cfg["files"]["flow"]["path"])
            ax_b.plot(
                flow_t, flow_df[fcfg["column"]].to_numpy(dtype=float),
                color=pal["flow"], linewidth=2.2, zorder=3,
            )
            ax_b.set_ylabel(fcfg.get("label", "Flow (GPM)"),
                            fontsize=fonts["axis_label"], color=pal["flow"])
            ax_b.tick_params(axis="y", colors=pal["flow"])
            if fcfg.get("ylim"):
                ax_b.set_ylim(fcfg["ylim"])

        if power_steps:
            ax_p = ax_b.twinx()
            ts = [float(s["t"]) for s in power_steps]
            kw = [float(s["kw"]) for s in power_steps]
            right = cfg["time"].get("xlim")
            ts.append(right[1] if right else max(temp_t[-1], ts[-1]))
            kw.append(kw[-1])
            ax_p.step(ts, kw, where="post", color=pal["power"],
                      linewidth=2.2, zorder=3)
            ax_p.set_ylabel("Rod power (kW)", fontsize=fonts["axis_label"],
                            color=pal["power"])
            ax_p.tick_params(axis="y", colors=pal["power"],
                             labelsize=fonts["tick"])
            ax_p.set_ylim(0, max(kw) * 1.35)
            ax_p.spines["top"].set_visible(False)

    # --- event lines through every panel ------------------------------------
    kinds = style["event_kinds"]
    for i, ev in enumerate(cfg.get("events", [])):
        k = kinds.get(ev.get("kind", "other"), kinds["other"])
        for ax in axes:
            ax.axvline(ev["t"], color=k["color"], linewidth=1.8,
                       dashes=k["dash"], zorder=5)
        if ev.get("label"):
            # Stagger labels so consecutive events do not overprint.
            y = 0.94 - 0.085 * (i % 3)
            ax_t.annotate(
                ev["label"], xy=(ev["t"], y),
                xycoords=ax_t.get_xaxis_transform(),
                xytext=(7, 0), textcoords="offset points",
                ha="left", va="top", fontsize=fonts["annotation"],
                color=k["color"], zorder=6,
                bbox=dict(boxstyle="round,pad=0.32", facecolor="white",
                          edgecolor=k["color"], linewidth=1.0, alpha=0.94),
            )

    # --- callouts -----------------------------------------------------------
    for c in cfg.get("callouts", []):
        ax_t.annotate(
            c["text"], xy=(c["t"], c["y"]),
            xytext=(c.get("dx", 14), c.get("dy", 18)),
            textcoords="offset points", fontsize=fonts["annotation"],
            color=pal["text"], zorder=7,
            arrowprops=dict(arrowstyle="-", color=pal["text"], linewidth=1.1),
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor=pal["text"], linewidth=0.9, alpha=0.94),
        )

    # --- axis cosmetics -----------------------------------------------------
    units = "min" if cfg["time"].get("units", "min") == "min" else "s"
    axes[-1].set_xlabel(f"Time ({units})", fontsize=fonts["axis_label"],
                        color=pal["text"])
    for ax in axes:
        ax.grid(True, which="major", color=pal["grid"], linewidth=0.9, zorder=1)
        ax.grid(True, which="minor", color=pal["grid"], linewidth=0.5,
                alpha=0.6, zorder=1)
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        ax.tick_params(labelsize=fonts["tick"])
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        if cfg["time"].get("xlim"):
            ax.set_xlim(cfg["time"]["xlim"])

    handles, labels = ax_t.get_legend_handles_labels()
    if handles:
        ax_t.legend(handles, labels, fontsize=fonts["legend"], frameon=True,
                    framealpha=0.94, edgecolor=pal["grid"],
                    loc=cfg.get("legend_loc", "best"))

    # --- titles -------------------------------------------------------------
    # Positions are computed in inches then converted to figure fractions, so
    # the header spacing stays correct at any figure size or font size.
    H = float(fig_cfg["height_in"])
    pad_in = 0.22
    y_cursor = H - pad_in

    if cfg.get("title"):
        y_cursor -= fonts["title"] / 72.0
        fig.text(0.010, y_cursor / H, cfg["title"], fontsize=fonts["title"],
                 fontweight="bold", color=pal["text"], ha="left", va="baseline")
    if cfg.get("subtitle"):
        y_cursor -= fonts["subtitle"] / 72.0 * 1.55
        fig.text(0.010, y_cursor / H, cfg["subtitle"],
                 fontsize=fonts["subtitle"], color="#4A4A4A",
                 ha="left", va="baseline")

    top = max(0.55, (y_cursor - 0.28) / H) if cfg.get("title") else 1.0
    fig.get_layout_engine().set(rect=(0.004, 0.004, 0.992, top - 0.004))
    return fig


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Build a poster-ready figure from one CORE^2S run folder."
    )
    ap.add_argument("run_folder", help="folder holding this run's CSVs")
    ap.add_argument("--reset", action="store_true",
                    help="overwrite annotations.json with a fresh starter file")
    ap.add_argument("--show", action="store_true",
                    help="also open the figure in a window")
    args = ap.parse_args()

    run_dir = Path(args.run_folder).expanduser().resolve()
    if not run_dir.is_dir():
        _fail(f"not a folder: {run_dir}")

    cfg_path = run_dir / "annotations.json"

    if args.reset or not cfg_path.exists():
        cfg_path.write_text(json.dumps(build_starter_config(run_dir), indent=2))
        print(f"\n[finalize_plot] Wrote starter file:\n    {cfg_path}\n")
        print("  Open it, fill in the title, events, power steps and spans,")
        print("  then run this command again to build the figure.")
        print("  Field-by-field docs are in the header of this script.\n")
        return

    cfg = json.loads(cfg_path.read_text())

    temp_df, temp_t = load_table(
        run_dir, cfg["files"].get("temperature"), cfg, "temperature")
    if temp_df is None:
        _fail("no temperature file configured in annotations.json")
    flow_df, flow_t = load_table(run_dir, cfg["files"].get("flow"), cfg, "flow")

    fig = draw(cfg, temp_df, temp_t, flow_df, flow_t)

    out_dir = run_dir / "poster"
    out_dir.mkdir(exist_ok=True)
    stem = cfg.get("output_name") or run_dir.name
    pdf, png = out_dir / f"{stem}.pdf", out_dir / f"{stem}.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=cfg["figure"].get("dpi", 200))

    print(f"\n[finalize_plot] Saved:\n    {pdf}   <- for print\n    {png}   <- preview\n")

    if args.show:
        matplotlib.use("TkAgg")
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
