from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_sample_flight() -> pd.DataFrame:
    df = pd.read_csv(DATA / "flight_a319_opensky.csv", parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["elapsed_min"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds() / 60
    df["dt_s"] = df["timestamp"].diff().dt.total_seconds().bfill().clip(lower=1)
    df["phase"] = np.select(
        [
            df["vertical_rate"] > 300,
            df["vertical_rate"] < -300,
        ],
        ["climb", "descent"],
        default="level",
    )
    return df


def add_synthetic_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Add a tiny weather-like layer for lecture reproducibility.

    The values are deliberately simple and local to the sample trajectory. They
    demonstrate the data flow without requiring a live ERA5/ARPEGE download.
    """
    out = df.copy()
    alt_kft = out["altitude"] / 1000.0
    cruise_peak = np.exp(-((alt_kft - 33.0) / 5.5) ** 2)
    longitude_peak = np.exp(-((out["longitude"] - out["longitude"].median()) / 1.2) ** 2)
    time_wave = 0.5 + 0.5 * np.sin(out["elapsed_min"] / out["elapsed_min"].max() * np.pi)

    out["temperature_k"] = 288.15 - 0.00198 * out["altitude"]
    out["relative_humidity_ice"] = 0.65 + 0.55 * cruise_peak * longitude_peak * time_wave
    out["issr"] = out["relative_humidity_ice"] > 1.0
    out["sac"] = (out["temperature_k"] < 233.0) & (out["altitude"] > 26000)
    out["persistent_contrail"] = out["issr"] & out["sac"]
    return out


def compute_openap_emissions(df: pd.DataFrame, actype: str = "A319", mass_takeoff: float = 62_000) -> pd.DataFrame:
    import openap

    out = df.copy()
    fuelflow = openap.FuelFlow(actype)
    emission = openap.Emission(actype)
    mass = mass_takeoff
    fuel_kg = []
    ff_kg_s = []
    co2_kg = []
    nox_g = []

    for row in out.itertuples(index=False):
        ff = float(
            fuelflow.enroute(
                mass=mass,
                tas=max(float(row.groundspeed), 120.0),
                alt=max(float(row.altitude), 1000.0),
                vs=float(row.vertical_rate),
            )
        )
        fuel = max(ff * float(row.dt_s), 0.0)
        fuel_kg.append(fuel)
        ff_kg_s.append(ff)
        co2_kg.append(float(emission.co2(ff) * row.dt_s / 1000.0))
        nox_g.append(float(emission.nox(ff, tas=max(row.groundspeed, 120.0), alt=max(row.altitude, 1000.0)) * row.dt_s))
        mass -= fuel

    out["fuel_flow_kg_s"] = ff_kg_s
    out["fuel_kg"] = fuel_kg
    out["co2_kg"] = co2_kg
    out["nox_g"] = nox_g
    out["mass_kg"] = mass_takeoff - out["fuel_kg"].cumsum()
    return out


def summarize_climate_tradeoff() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trajectory": ["observed", "fuel-optimal", "contrail-aware"],
            "relative_fuel": [1.00, 0.96, 1.02],
            "relative_co2": [1.00, 0.96, 1.02],
            "contrail_exposure": [1.00, 0.90, 0.42],
        }
    )


def plot_trajectory(df: pd.DataFrame):
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    fig = plt.figure(figsize=(6.4, 4.2))
    ax = plt.axes(projection=ccrs.LambertConformal(central_longitude=float(df["longitude"].median())))
    colors = {"climb": "#2a9d55", "level": "#0076a8", "descent": "#d06b2c"}

    lon_margin = max((df["longitude"].max() - df["longitude"].min()) * 0.12, 0.7)
    lat_margin = max((df["latitude"].max() - df["latitude"].min()) * 0.18, 0.45)
    ax.set_extent(
        [
            float(df["longitude"].min() - lon_margin),
            float(df["longitude"].max() + lon_margin),
            float(df["latitude"].min() - lat_margin),
            float(df["latitude"].max() + lat_margin),
        ],
        crs=ccrs.PlateCarree(),
    )
    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f3f4ef", edgecolor="none", zorder=0)
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#e8f4fb", edgecolor="none", zorder=0)
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), edgecolor="#87919b", linewidth=0.7)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), edgecolor="#a0a8b0", linewidth=0.45)
    ax.add_feature(cfeature.LAKES.with_scale("50m"), facecolor="#e8f4fb", edgecolor="#a0a8b0", linewidth=0.3)

    transform = ccrs.PlateCarree()
    ax.plot(df["longitude"], df["latitude"], color="#7b8794", linewidth=1.1, transform=transform, zorder=2)
    for phase, group in df.groupby("phase", sort=False):
        ax.scatter(
            group["longitude"],
            group["latitude"],
            s=34,
            label=phase,
            color=colors.get(phase, "#444"),
            edgecolor="white",
            linewidth=0.35,
            transform=transform,
            zorder=3,
        )
    gl = ax.gridlines(draw_labels=True, linewidth=0.35, color="#9aa6b2", alpha=0.65, linestyle="--")
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 8}
    gl.ylabel_style = {"size": 8}
    ax.set_title("Sample OpenSky trajectory")
    ax.legend(frameon=True, framealpha=0.92, loc="lower right", fontsize=8)
    plt.close(fig)
    return fig


def plot_vertical_profile(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(df["elapsed_min"], df["altitude"] / 1000, color="#0076a8", linewidth=2)
    mask = (
        df["persistent_contrail"].to_numpy(dtype=bool)
        if "persistent_contrail" in df
        else np.zeros(len(df), dtype=bool)
    )
    ax.fill_between(
        df["elapsed_min"],
        0,
        df["altitude"] / 1000,
        where=mask,
        color="#d06b2c",
        alpha=0.28,
        label="persistent-contrail segment",
    )
    ax.set_xlabel("Elapsed time (min)")
    ax.set_ylabel("Altitude (kft)")
    ax.set_title("Vertical profile of the trajectory")
    ax.grid(alpha=0.25)
    if "persistent_contrail" in df:
        ax.legend(frameon=False)
    plt.close(fig)
    return fig


def plot_emission_timeseries(df: pd.DataFrame):
    fig, axes = plt.subplots(2, 2, figsize=(16, 5.2), sharex=True)
    x = df["elapsed_min"]

    axes[0, 0].plot(x, df["fuel_flow_kg_s"], color="#0076a8", linewidth=1.8)
    axes[0, 0].set_title("Fuel flow")
    axes[0, 0].set_ylabel("kg/s")

    axes[1, 0].plot(x, df["fuel_kg"].cumsum(), color="#d06b2c", linewidth=1.8)
    axes[1, 0].set_title("Fuel")
    axes[1, 0].set_ylabel("kg")
    axes[1, 0].set_xlabel("Elapsed time (min)")

    co2_rate = df["co2_kg"] / df["dt_s"].clip(lower=1)
    axes[0, 1].plot(x, co2_rate, color="#2a9d55", linewidth=1.8)
    axes[0, 1].set_title("CO2 rate")
    axes[0, 1].set_ylabel("kg/s")

    nox_rate = df["nox_g"] / df["dt_s"].clip(lower=1)
    axes[1, 1].plot(x, nox_rate, color="#7a4cb0", linewidth=1.8)
    axes[1, 1].set_title("NOx rate")
    axes[1, 1].set_ylabel("g/s")
    axes[1, 1].set_xlabel("Elapsed time (min)")

    for ax in axes.ravel():
        ax.grid(alpha=0.25)

    fig.tight_layout()
    plt.close(fig)
    return fig


def plot_tradeoff(summary: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    x = np.arange(len(summary))
    width = 0.26
    ax.bar(x - width, summary["relative_fuel"], width, label="fuel", color="#0076a8")
    ax.bar(x, summary["relative_co2"], width, label="CO2", color="#2a9d55")
    ax.bar(x + width, summary["contrail_exposure"], width, label="contrail exposure", color="#d06b2c")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["trajectory"])
    ax.set_ylim(0, 1.2)
    ax.set_ylabel("Relative to observed")
    ax.set_title("Illustrative climate-routing trade-off")
    ax.legend(frameon=False, ncol=3)
    ax.grid(axis="y", alpha=0.25)
    plt.close(fig)
    return fig
