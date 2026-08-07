# -*- coding: utf-8 -*-
"""
SMR thermal loop run analyzer.

This script lives in the "data" folder and looks inside the run-parent
folder (currently "002") for LabVIEW run folders.

Expected structure:

    .../resources/v0.1.2/data/
        analyze_run.py
        002/
            run_YYYYMMDD_HHMMSS_tick/
                temperature.csv
                pressure.csv
                flow.csv
                voltage.csv          (optional - newer runs only)

Default behavior:
    - Analyzes the latest run folder
    - Creates up to 5 plots:
        1. temperature_over_time
        2. pressure_over_time
        3. flow_over_time              (heat exchanger flow)
        4. main_loop_flow_over_time    (if the column exists)
        5. voltage_over_time           (if voltage.csv exists)
       plus power_over_time if voltage.csv carries a watts column.
    - Excludes all average/summary columns
    - For flow, plots only the GPM flow columns, not raw voltage
    - Main loop flow is plotted separately from heat exchanger flow
      because the two differ by more than an order of magnitude
      (roughly 60 GPM vs a few GPM), so sharing one axis would
      flatten the heat exchanger trace into the baseline.
    - voltage.csv is optional: runs recorded before it was added
      still analyze normally, that plot is just skipped.

Notes on speed:
    - PNG only by default (PDF is vector and is very slow for large runs)
    - Non-interactive Agg backend so no figure windows are created
    - Points per line are capped, and the "tight bbox" second render pass
      has been removed
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

import matplotlib


# -------------------------------------------------------------------------
# User-adjustable settings
# -------------------------------------------------------------------------

# Which folder inside "data" holds the run folders.
# Set to None to always auto-detect the highest-numbered folder.
RUN_FOLDER_PARENT_NAME = "002"

# If the folder above is missing, fall back to the highest-numbered
# folder that exists (001, 002, 003, ...). Makes future migrations painless.
AUTO_DETECT_RUN_PARENT = True

# Maximum number of points plotted per line.
# This keeps graphs fast even for very large CSV files.
MAX_PLOT_POINTS = 3000

# Save both PNG and PDF?
# PDF is vector: every plotted point becomes path data in the file.
# Leave this False unless you specifically need a vector figure.
SAVE_PDF = False
SAVE_PNG = True

# Output resolution for PNG. 300 is print quality but ~4x the pixels of 150.
PNG_DPI = 150

# Use a non-interactive plotting backend (no figure windows, much faster
# and avoids Spyder/Qt backend stalls). Set False if you want inline plots.
USE_NON_INTERACTIVE_BACKEND = True


if USE_NON_INTERACTIVE_BACKEND:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  (must come after matplotlib.use)


# Line-drawing speedups for dense data.
matplotlib.rcParams["path.simplify"] = True
matplotlib.rcParams["path.simplify_threshold"] = 1.0
matplotlib.rcParams["agg.path.chunksize"] = 10000


# -------------------------------------------------------------------------
# Folder discovery
# -------------------------------------------------------------------------

def numbered_subfolders(folder: Path) -> list[Path]:
    """Return subfolders whose names are all digits (001, 002, ...), sorted."""
    if not folder.is_dir():
        return []

    return sorted(
        (p for p in folder.iterdir() if p.is_dir() and p.name.isdigit()),
        key=lambda p: p.name,
    )


def looks_like_data_dir(folder: Path) -> bool:
    """True if this folder contains the run-parent folder."""
    if not folder.is_dir():
        return False

    if RUN_FOLDER_PARENT_NAME and (folder / RUN_FOLDER_PARENT_NAME).is_dir():
        return True

    return AUTO_DETECT_RUN_PARENT and bool(numbered_subfolders(folder))


def find_data_dir() -> Path:
    """
    Find the data folder that contains the run-parent folder.

    Priority:
    1. Folder containing this script
    2. Current Spyder/terminal working directory
    """
    candidates: list[Path] = []

    try:
        candidates.append(Path(__file__).resolve().parent)
    except NameError:
        # __file__ is undefined when code is pasted straight into a console.
        pass

    candidates.append(Path.cwd().resolve())

    for candidate in candidates:
        # Case: candidate is the data folder.
        if looks_like_data_dir(candidate):
            return candidate

        # Case: candidate is the version folder and contains data/002.
        if looks_like_data_dir(candidate / "data"):
            return candidate / "data"

        # Case: candidate is already the 002 folder.
        if candidate.name.isdigit() and looks_like_data_dir(candidate.parent):
            return candidate.parent

    raise FileNotFoundError(
        f"Could not find the data folder containing '{RUN_FOLDER_PARENT_NAME}'. "
        "Make sure analyze_run.py is saved in the data folder "
        "(.../resources/v0.1.2/data)."
    )


def find_run_parent(data_dir: Path) -> Path:
    """Return the folder that holds the run_* folders (normally data/002)."""
    if RUN_FOLDER_PARENT_NAME:
        explicit = data_dir / RUN_FOLDER_PARENT_NAME
        if explicit.is_dir():
            return explicit

    if AUTO_DETECT_RUN_PARENT:
        numbered = numbered_subfolders(data_dir)
        if numbered:
            return numbered[-1]

    raise FileNotFoundError(
        f"No run-parent folder found inside {data_dir}. "
        f"Expected a folder named '{RUN_FOLDER_PARENT_NAME}'."
    )


DATA_DIR = find_data_dir()
RUN_PARENT = find_run_parent(DATA_DIR)


FILE_CANDIDATES = {
    "temperature": [
        "temperature.csv",
        "Temperature_Log.csv",
        "Temperature.csv",
        "temp.csv",
    ],
    "pressure": [
        "pressure.csv",
        "Pressure_Log.csv",
        "Pressure.csv",
    ],
    "flow": [
        "flow.csv",
        "Flow_Log.csv",
        "Flow.csv",
    ],
    "voltage": [
        "voltage.csv",
        "Voltage_Log.csv",
        "Voltage.csv",
        "power.csv",
    ],
}

# Kinds that older runs will not have. Missing these is not an error.
OPTIONAL_FILE_KINDS = {"voltage"}


def find_run_folders() -> list[Path]:
    """Return available run folders inside the run parent."""
    if not RUN_PARENT.exists():
        raise FileNotFoundError(f"Run parent folder does not exist: {RUN_PARENT}")

    run_folders = [
        p for p in RUN_PARENT.iterdir()
        if p.is_dir() and p.name.startswith("run_")
    ]

    if not run_folders:
        run_folders = [
            p for p in RUN_PARENT.iterdir()
            if p.is_dir() and p.name != "plots"
        ]

    return sorted(run_folders, key=lambda p: p.name)


def get_latest_run_folder() -> Path:
    """Return the latest run folder by sorted folder name."""
    run_folders = find_run_folders()

    if not run_folders:
        raise FileNotFoundError(f"No run folders found in {RUN_PARENT}")

    return run_folders[-1]


def resolve_run_folder(run_argument: str | None) -> Path:
    """Resolve a run folder from a command-line argument."""
    if run_argument is None or run_argument.lower() == "latest":
        return get_latest_run_folder()

    candidate = Path(run_argument)

    if candidate.exists() and candidate.is_dir():
        return candidate

    candidate = RUN_PARENT / run_argument

    if candidate.exists() and candidate.is_dir():
        return candidate

    raise FileNotFoundError(f"Could not find run folder: {run_argument}")


def find_csv_file(run_folder: Path, kind: str) -> Path:
    """Find the CSV file for temperature, pressure, or flow."""
    for filename in FILE_CANDIDATES[kind]:
        candidate = run_folder / filename
        if candidate.exists():
            return candidate

    matches = [
        p for p in run_folder.glob("*.csv")
        if kind.lower() in p.stem.lower()
    ]

    if matches:
        return sorted(matches, key=lambda p: p.name)[0]

    raise FileNotFoundError(
        f"Could not find {kind} CSV in {run_folder}. "
        f"Expected one of: {FILE_CANDIDATES[kind]}"
    )


def find_optional_csv_file(run_folder: Path, kind: str) -> Path | None:
    """
    Same as find_csv_file, but returns None instead of raising.

    Used for files that only exist in newer runs, so that older run
    folders still analyze without error.
    """
    try:
        return find_csv_file(run_folder, kind)
    except FileNotFoundError:
        return None


# -------------------------------------------------------------------------
# Data handling
# -------------------------------------------------------------------------

def get_time_column(df: pd.DataFrame) -> str:
    """Find the time column. Defaults to the first column."""
    for col in df.columns:
        if "time" in col.lower():
            return col

    return df.columns[0]


def read_clean_csv(path: Path) -> pd.DataFrame:
    """Read a CSV and clean blank/non-numeric rows."""
    df = pd.read_csv(path)

    df.columns = [str(col).strip() for col in df.columns]

    df = df.dropna(how="all")

    # Convert everything at once instead of column-by-column assignment.
    df = df.apply(pd.to_numeric, errors="coerce")

    time_col = get_time_column(df)
    df = df.dropna(subset=[time_col])

    return df


def is_average_or_summary_column(column_name: str) -> bool:
    """Return True if the column is an average/summary column."""
    lower = column_name.lower()

    keywords = [
        "avg",
        "average",
        "overall",
        # Narrowed from a bare "main loop" so that a real measured
        # channel named "Main Loop Flow (GPM)" is not silently dropped.
        # The averaged columns are still caught by "avg" above.
        "main loop avg",
        "heat exchanger avg",
        "hx avg",
        "hxpressure",
        "hx pressure",
    ]

    return any(keyword in lower for keyword in keywords)


def is_main_loop_column(column_name: str) -> bool:
    """Return True if the column belongs to the main loop rather than the HX."""
    return "main loop" in column_name.lower()


def is_power_column(column_name: str) -> bool:
    """Return True if the column is a power column in watts or kilowatts."""
    lower = column_name.lower()

    keywords = [
        "(w)",
        "(kw)",
        "power",
        "watt",
    ]

    return any(keyword in lower for keyword in keywords)


def is_raw_voltage_column(column_name: str) -> bool:
    """Return True if the column is a raw voltage column."""
    lower = column_name.lower()

    keywords = [
        "raw",
        "voltage",
        "(v)",
        " volts",
    ]

    return any(keyword in lower for keyword in keywords)


def downsample_dataframe(df: pd.DataFrame, max_points: int = MAX_PLOT_POINTS) -> pd.DataFrame:
    """
    Downsample a dataframe for plotting speed.

    This does not alter the CSV file. It only reduces how many points are drawn.
    """
    if len(df) <= max_points:
        return df

    step = max(1, len(df) // max_points)
    return df.iloc[::step, :].copy()


# -------------------------------------------------------------------------
# Plotting
# -------------------------------------------------------------------------

def plot_dataframe(
    df: pd.DataFrame,
    title: str,
    y_label: str,
    output_stem: Path,
    columns_to_plot: list[str],
    time_units: str = "minutes",
    max_points: int = MAX_PLOT_POINTS,
) -> None:
    """Plot selected columns against time and save the graph."""
    if not columns_to_plot:
        raise ValueError(f"No columns selected for plot: {title}")

    start = time.time()

    df_plot = downsample_dataframe(df, max_points)

    print(
        f"  Rendering '{title}': "
        f"{len(columns_to_plot)} lines x {len(df_plot)} points",
        flush=True,
    )

    time_col = get_time_column(df_plot)

    if time_units == "minutes":
        time_axis = df_plot[time_col] / 60.0
        x_label = "Time (minutes)"
    elif time_units == "seconds":
        time_axis = df_plot[time_col]
        x_label = "Time (seconds)"
    else:
        raise ValueError(f"Unsupported time_units: {time_units}")

    fig, ax = plt.subplots(figsize=(12, 7))

    for col in columns_to_plot:
        if col not in df_plot.columns:
            continue

        ax.plot(
            time_axis,
            df_plot[col],
            label=col,
            linewidth=1.0,
        )

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, alpha=0.35)

    ax.legend(
        fontsize=7,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        borderaxespad=0.0,
    )

    # Reserve room for the legend directly instead of using
    # bbox_inches="tight", which forces a second full render of the figure.
    fig.subplots_adjust(left=0.08, right=0.78, top=0.93, bottom=0.09)

    if SAVE_PNG:
        png_path = output_stem.with_suffix(".png")
        fig.savefig(png_path, dpi=PNG_DPI, facecolor="white")
        print(f"  Saved: {png_path}", flush=True)

    if SAVE_PDF:
        pdf_path = output_stem.with_suffix(".pdf")
        fig.savefig(pdf_path, facecolor="white")
        print(f"  Saved: {pdf_path}", flush=True)

    plt.close(fig)

    print(f"  Done in {time.time() - start:.1f} s", flush=True)
    print(flush=True)


def get_temperature_columns(df: pd.DataFrame) -> list[str]:
    """
    Select only individual thermocouple columns.

    Excludes average/summary columns.
    """
    time_col = get_time_column(df)

    selected = []

    for col in df.columns:
        if col == time_col:
            continue

        if is_average_or_summary_column(col):
            continue

        selected.append(col)

    return selected


def get_pressure_columns(df: pd.DataFrame) -> list[str]:
    """
    Select only individual pressure transducer columns.

    Excludes average/summary columns.
    """
    time_col = get_time_column(df)

    selected = []

    for col in df.columns:
        if col == time_col:
            continue

        if is_average_or_summary_column(col):
            continue

        selected.append(col)

    return selected


def get_flow_columns(df: pd.DataFrame) -> list[str]:
    """
    Select heat exchanger flow in GPM.

    Excludes raw voltage, signal amplitude, average/summary columns,
    and main loop flow (which is plotted separately because of scale).
    """
    time_col = get_time_column(df)

    selected = []

    for col in df.columns:
        if col == time_col:
            continue

        if is_raw_voltage_column(col):
            continue

        if is_average_or_summary_column(col):
            continue

        if is_main_loop_column(col):
            continue

        lower = col.lower()

        # Prefer columns that explicitly look like flow/GPM.
        if "gpm" in lower or "flow" in lower:
            selected.append(col)

    # Fallback: if no explicit GPM/flow column was found, use the first non-time,
    # non-voltage, non-average column.
    if not selected:
        for col in df.columns:
            if col == time_col:
                continue

            if is_raw_voltage_column(col):
                continue

            if is_average_or_summary_column(col):
                continue

            if is_main_loop_column(col):
                continue

            selected.append(col)
            break

    return selected


def get_main_loop_flow_columns(df: pd.DataFrame) -> list[str]:
    """
    Select main loop flow in GPM.

    Returns an empty list for older runs that predate this column.
    """
    time_col = get_time_column(df)

    selected = []

    for col in df.columns:
        if col == time_col:
            continue

        if is_raw_voltage_column(col):
            continue

        if is_average_or_summary_column(col):
            continue

        if not is_main_loop_column(col):
            continue

        lower = col.lower()

        if "gpm" in lower or "flow" in lower:
            selected.append(col)

    return selected


def get_voltage_columns(df: pd.DataFrame) -> list[str]:
    """
    Select voltage columns from voltage.csv.

    Note this deliberately does NOT use is_raw_voltage_column, which exists
    to strip voltages out of the flow plot. Here the voltages are the point.
    """
    time_col = get_time_column(df)

    selected = []

    for col in df.columns:
        if col == time_col:
            continue

        if is_power_column(col):
            continue

        lower = col.lower()

        if "(v)" in lower or "volt" in lower:
            selected.append(col)

    return selected


def get_power_columns(df: pd.DataFrame) -> list[str]:
    """
    Select power columns from voltage.csv.

    Plotted on their own axis: watts and volts differ by roughly three
    orders of magnitude, so sharing an axis would flatten the voltage trace.
    """
    time_col = get_time_column(df)

    return [
        col for col in df.columns
        if col != time_col and is_power_column(col)
    ]


def print_variation_summary(df: pd.DataFrame, columns: list[str]) -> None:
    """
    Print min/max/mean/spread for each column.

    Added for the rod voltage file specifically: the reason that file
    exists is to quantify how much the supply drifts over a run, and
    the numbers are easier to compare than eyeballing the plot.
    """
    for col in columns:
        series = df[col].dropna()

        if series.empty:
            continue

        low = series.min()
        high = series.max()
        mean = series.mean()
        spread = high - low
        percent = (spread / mean * 100.0) if mean else float("nan")

        print(
            f"  {col}: min {low:.4f}, max {high:.4f}, mean {mean:.4f}, "
            f"spread {spread:.4f} ({percent:.1f}% of mean)",
            flush=True,
        )


# -------------------------------------------------------------------------
# Main analysis
# -------------------------------------------------------------------------

def analyze_run(
    run_folder: Path,
    time_units: str = "minutes",
    max_points: int = MAX_PLOT_POINTS,
) -> None:
    """
    Load one run folder and generate its plots.

    Always: temperature, pressure, heat exchanger flow.
    When the columns/files exist: main loop flow, rod voltage, rod power.
    """
    print(flush=True)
    print("Using data folder:", flush=True)
    print(DATA_DIR, flush=True)
    print(flush=True)
    print("Run parent folder:", flush=True)
    print(RUN_PARENT, flush=True)
    print(flush=True)
    print("Analyzing run folder:", flush=True)
    print(run_folder, flush=True)
    print(flush=True)

    temperature_csv = find_csv_file(run_folder, "temperature")
    pressure_csv = find_csv_file(run_folder, "pressure")
    flow_csv = find_csv_file(run_folder, "flow")
    voltage_csv = find_optional_csv_file(run_folder, "voltage")

    print(f"Temperature CSV: {temperature_csv.name}", flush=True)
    print(f"Pressure CSV:    {pressure_csv.name}", flush=True)
    print(f"Flow CSV:        {flow_csv.name}", flush=True)
    print(
        f"Voltage CSV:     "
        f"{voltage_csv.name if voltage_csv else '(not present in this run)'}",
        flush=True,
    )
    print(flush=True)

    temperature_df = read_clean_csv(temperature_csv)
    pressure_df = read_clean_csv(pressure_csv)
    flow_df = read_clean_csv(flow_csv)
    voltage_df = read_clean_csv(voltage_csv) if voltage_csv else None

    print(
        f"Rows loaded -> temperature: {len(temperature_df)}, "
        f"pressure: {len(pressure_df)}, flow: {len(flow_df)}"
        + (f", voltage: {len(voltage_df)}" if voltage_df is not None else ""),
        flush=True,
    )
    print(flush=True)

    plots_dir = run_folder / "plots"
    plots_dir.mkdir(exist_ok=True)

    temperature_columns = get_temperature_columns(temperature_df)
    pressure_columns = get_pressure_columns(pressure_df)
    flow_columns = get_flow_columns(flow_df)
    main_loop_flow_columns = get_main_loop_flow_columns(flow_df)

    if voltage_df is not None:
        voltage_columns = get_voltage_columns(voltage_df)
        power_columns = get_power_columns(voltage_df)
    else:
        voltage_columns = []
        power_columns = []

    print("Temperature columns plotted:", flush=True)
    print(temperature_columns, flush=True)
    print(flush=True)

    print("Pressure columns plotted:", flush=True)
    print(pressure_columns, flush=True)
    print(flush=True)

    print("Heat exchanger flow columns plotted:", flush=True)
    print(flow_columns, flush=True)
    print(flush=True)

    print("Main loop flow columns plotted:", flush=True)
    print(main_loop_flow_columns or "(none found in this run)", flush=True)
    print(flush=True)

    print("Voltage columns plotted:", flush=True)
    print(voltage_columns or "(none found in this run)", flush=True)
    print(flush=True)

    if power_columns:
        print("Power columns plotted:", flush=True)
        print(power_columns, flush=True)
        print(flush=True)

    plot_dataframe(
        temperature_df,
        title="Temperature Over Time",
        y_label="Temperature (°C)",
        output_stem=plots_dir / "temperature_over_time",
        columns_to_plot=temperature_columns,
        time_units=time_units,
        max_points=max_points,
    )

    plot_dataframe(
        pressure_df,
        title="Pressure Over Time",
        y_label="Pressure (psi)",
        output_stem=plots_dir / "pressure_over_time",
        columns_to_plot=pressure_columns,
        time_units=time_units,
        max_points=max_points,
    )

    plot_dataframe(
        flow_df,
        title="Heat Exchanger Flow Over Time",
        y_label="Flow (GPM)",
        output_stem=plots_dir / "flow_over_time",
        columns_to_plot=flow_columns,
        time_units=time_units,
        max_points=max_points,
    )

    if main_loop_flow_columns:
        plot_dataframe(
            flow_df,
            title="Main Loop Flow Over Time",
            y_label="Flow (GPM)",
            output_stem=plots_dir / "main_loop_flow_over_time",
            columns_to_plot=main_loop_flow_columns,
            time_units=time_units,
            max_points=max_points,
        )
    else:
        print("Skipping main loop flow plot: no matching column.", flush=True)
        print(flush=True)

    if voltage_df is not None and voltage_columns:
        plot_dataframe(
            voltage_df,
            title="Rod Voltage Over Time",
            y_label="Voltage (V)",
            output_stem=plots_dir / "voltage_over_time",
            columns_to_plot=voltage_columns,
            time_units=time_units,
            max_points=max_points,
        )

        print("Rod voltage variation over this run:", flush=True)
        print_variation_summary(voltage_df, voltage_columns)
        print(flush=True)
    else:
        print("Skipping voltage plot: no voltage.csv in this run.", flush=True)
        print(flush=True)

    if voltage_df is not None and power_columns:
        plot_dataframe(
            voltage_df,
            title="Rod Power Over Time",
            y_label="Power (W)",
            output_stem=plots_dir / "power_over_time",
            columns_to_plot=power_columns,
            time_units=time_units,
            max_points=max_points,
        )

        print("Rod power variation over this run:", flush=True)
        print_variation_summary(voltage_df, power_columns)
        print(flush=True)

    print("Finished.", flush=True)
    print("Plots saved in:", flush=True)
    print(plots_dir, flush=True)


def list_runs() -> None:
    """Print all available run folders."""
    run_folders = find_run_folders()

    if not run_folders:
        print(f"No run folders found in {RUN_PARENT}")
        return

    print(f"Available runs in {RUN_PARENT}:")
    for run in run_folders:
        print(f"  {run.name}")


def get_script_arguments() -> list[str]:
    """
    Return command-line arguments, ignoring the ones Spyder/Jupyter inject.

    When a script is run inside an IPython kernel, sys.argv can contain
    things like ['-f', '/path/kernel-1234.json'], which argparse would
    reject and then call sys.exit() on.
    """
    argv = sys.argv[1:]

    if any(arg == "-f" or arg.endswith(".json") for arg in argv):
        return []

    return argv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze SMR thermal loop LabVIEW CSV data."
    )

    parser.add_argument(
        "--run",
        default="latest",
        help=(
            "Run folder to analyze. Use 'latest', a run folder name, "
            "or a full path. Default: latest."
        ),
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available run folders and exit.",
    )

    parser.add_argument(
        "--time-units",
        choices=["minutes", "seconds"],
        default="minutes",
        help="Time axis units. Default: minutes.",
    )

    parser.add_argument(
        "--max-points",
        type=int,
        default=MAX_PLOT_POINTS,
        help=f"Max points drawn per line. Default: {MAX_PLOT_POINTS}.",
    )

    args, unknown = parser.parse_known_args(get_script_arguments())

    if unknown:
        print(f"Ignoring unrecognized arguments: {unknown}", flush=True)

    if args.list:
        list_runs()
        return

    run_folder = resolve_run_folder(args.run)
    analyze_run(
        run_folder,
        time_units=args.time_units,
        max_points=args.max_points,
    )


if __name__ == "__main__":
    main()
