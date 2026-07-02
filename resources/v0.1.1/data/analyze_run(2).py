
# -*- coding: utf-8 -*-
"""
SMR thermal loop run analyzer.

This script lives in the "data" folder and looks inside "data/001"
for LabVIEW run folders.

Expected structure:

data/
    analyze_run.py
    001/
        run_YYYYMMDD_HHMMSS_tick/
            temperature.csv
            pressure.csv
            flow.csv

Default behavior:
    - Analyzes the latest run folder
    - Creates 3 plots:
        1. temperature_over_time
        2. pressure_over_time
        3. flow_over_time
    - Excludes all average/summary columns
    - For flow, plots only the GPM flow column, not raw voltage
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# -------------------------------------------------------------------------
# User-adjustable settings
# -------------------------------------------------------------------------

RUN_FOLDER_PARENT_NAME = "001"

# Maximum number of points plotted per line.
# This keeps graphs fast even for very large CSV files.
MAX_PLOT_POINTS = 10000

# Save both PNG and PDF?
SAVE_PDF = True
SAVE_PNG = True


# -------------------------------------------------------------------------
# Folder discovery
# -------------------------------------------------------------------------

def find_data_dir() -> Path:
    """
    Find the data folder that contains the 001 run folder.

    Priority:
    1. Folder containing this script
    2. Current Spyder/terminal working directory
    """
    candidates = [
        Path(__file__).resolve().parent,
        Path.cwd(),
    ]

    for candidate in candidates:
        candidate = candidate.resolve()

        # Case: candidate is the data folder.
        if (candidate / RUN_FOLDER_PARENT_NAME).exists():
            return candidate

        # Case: candidate is the repo folder and contains data/001.
        if (candidate / "data" / RUN_FOLDER_PARENT_NAME).exists():
            return candidate / "data"

        # Case: candidate is already the 001 folder.
        if candidate.name == RUN_FOLDER_PARENT_NAME:
            return candidate.parent

    raise FileNotFoundError(
        "Could not find the data folder containing '001'. "
        "Make sure analyze_run.py is saved in the GitHub data folder."
    )


DATA_DIR = find_data_dir()
RUN_PARENT = DATA_DIR / RUN_FOLDER_PARENT_NAME


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
}


def find_run_folders() -> list[Path]:
    """Return available run folders inside data/001."""
    if not RUN_PARENT.exists():
        raise FileNotFoundError(f"Run parent folder does not exist: {RUN_PARENT}")

    run_folders = [
        p for p in RUN_PARENT.iterdir()
        if p.is_dir() and p.name.startswith("run_")
    ]

    if not run_folders:
        run_folders = [
            p for p in RUN_PARENT.iterdir()
            if p.is_dir()
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

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

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
        "main loop",
        "heat exchanger avg",
        "hx avg",
        "hxpressure",
        "hx pressure",
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
) -> None:
    """Plot selected columns against time and save the graph."""
    if not columns_to_plot:
        raise ValueError(f"No columns selected for plot: {title}")

    df_plot = downsample_dataframe(df)

    time_col = get_time_column(df_plot)

    if time_units == "minutes":
        time = df_plot[time_col] / 60.0
        x_label = "Time (minutes)"
    elif time_units == "seconds":
        time = df_plot[time_col]
        x_label = "Time (seconds)"
    else:
        raise ValueError(f"Unsupported time_units: {time_units}")

    fig, ax = plt.subplots(figsize=(12, 7))

    for col in columns_to_plot:
        if col not in df_plot.columns:
            continue

        ax.plot(
            time,
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

    fig.tight_layout()

    if SAVE_PNG:
        png_path = output_stem.with_suffix(".png")
        fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"Saved: {png_path}")

    if SAVE_PDF:
        pdf_path = output_stem.with_suffix(".pdf")
        fig.savefig(pdf_path, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"Saved: {pdf_path}")

    plt.close(fig)


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
    Select only flow in GPM.

    Excludes raw voltage and average/summary columns.
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

            selected.append(col)
            break

    return selected


# -------------------------------------------------------------------------
# Main analysis
# -------------------------------------------------------------------------

def analyze_run(run_folder: Path, time_units: str = "minutes") -> None:
    """Load one run folder and generate temperature, pressure, and flow plots."""
    print()
    print(f"Using data folder:")
    print(DATA_DIR)
    print()
    print(f"Analyzing run folder:")
    print(run_folder)
    print()

    temperature_csv = find_csv_file(run_folder, "temperature")
    pressure_csv = find_csv_file(run_folder, "pressure")
    flow_csv = find_csv_file(run_folder, "flow")

    print(f"Temperature CSV: {temperature_csv.name}")
    print(f"Pressure CSV:    {pressure_csv.name}")
    print(f"Flow CSV:        {flow_csv.name}")
    print()

    temperature_df = read_clean_csv(temperature_csv)
    pressure_df = read_clean_csv(pressure_csv)
    flow_df = read_clean_csv(flow_csv)

    plots_dir = run_folder / "plots"
    plots_dir.mkdir(exist_ok=True)

    temperature_columns = get_temperature_columns(temperature_df)
    pressure_columns = get_pressure_columns(pressure_df)
    flow_columns = get_flow_columns(flow_df)

    print("Temperature columns plotted:")
    print(temperature_columns)
    print()

    print("Pressure columns plotted:")
    print(pressure_columns)
    print()

    print("Flow columns plotted:")
    print(flow_columns)
    print()

    plot_dataframe(
        temperature_df,
        title="Temperature Over Time",
        y_label="Temperature (°C)",
        output_stem=plots_dir / "temperature_over_time",
        columns_to_plot=temperature_columns,
        time_units=time_units,
    )

    plot_dataframe(
        pressure_df,
        title="Pressure Over Time",
        y_label="Pressure (psi)",
        output_stem=plots_dir / "pressure_over_time",
        columns_to_plot=pressure_columns,
        time_units=time_units,
    )

    plot_dataframe(
        flow_df,
        title="Heat Exchanger Flow Over Time",
        y_label="Flow (GPM)",
        output_stem=plots_dir / "flow_over_time",
        columns_to_plot=flow_columns,
        time_units=time_units,
    )

    print()
    print("Finished.")
    print(f"Plots saved in:")
    print(plots_dir)


def list_runs() -> None:
    """Print all available run folders."""
    run_folders = find_run_folders()

    if not run_folders:
        print(f"No run folders found in {RUN_PARENT}")
        return

    print(f"Available runs in {RUN_PARENT}:")
    for run in run_folders:
        print(f"  {run.name}")


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

    args = parser.parse_args()

    if args.list:
        list_runs()
        return

    run_folder = resolve_run_folder(args.run)
    analyze_run(run_folder, time_units=args.time_units)


if __name__ == "__main__":
    main()