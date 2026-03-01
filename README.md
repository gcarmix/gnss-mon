# GNSS Monitor

A desktop application for visualizing GNSS satellite constellations from broadcast ephemeris data. Load RINEX 3 navigation files, project satellite positions onto a polar skyplot, inspect ephemeris parameters, and step forward or backward in time to observe constellation geometry changes.

## Features

- **RINEX 3 Navigation File Loading** — Parse broadcast ephemeris for GPS, Galileo, GLONASS, and BeiDou constellations
- **Satellite Skyplot** — Polar azimuth/elevation plot showing visible satellites from an observer position, color-coded by constellation
- **Ephemeris Tables** — Detailed orbital parameter inspection per constellation (Keplerian elements for GPS/Galileo/BeiDou, state vectors for GLONASS)
- **Time Forwarding** — Step forward/backward through time with configurable intervals, or auto-play to animate constellation motion
- **GNSS Time Systems** — Live display of UTC, GPST, GST, BDT, and GLONASS time with week/ToW
- **Synthetic RINEX Export** — Generate adjusted RINEX 3.04 files from the current simulation state
- **Configurable Observer** — Set geodetic coordinates (lat, lon, alt) to compute azimuth and elevation for your location

## Supported Constellations

| Constellation | Prefix | Propagation Method |
|---|---|---|
| GPS | G | Keplerian (IS-GPS-200) |
| Galileo | E | Keplerian |
| BeiDou | C | Keplerian |
| GLONASS | R | RK4 numerical integration |

## Installation

Requires Python 3.12+.

```bash
cd gnss-mon
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Dependencies

- **PyQt6** — GUI framework
- **matplotlib** — Skyplot visualization
- **numpy** — Numerical computation
- **georinex** — RINEX file parsing
- **xarray** — Multi-dimensional array handling

## Usage

```bash
python main.py
```

1. **Load a RINEX file** — `File → Open RINEX File` (Ctrl+O) to load a RINEX 3 broadcast navigation file
2. **Set observer position** — `File → Set Observer Position` (Ctrl+L) to enter your geodetic coordinates
3. **Navigate in time** — Use the time control bar to step forward/backward, jump to a specific time, or press Play for continuous animation
4. **Explore tabs**:
   - **Skyplot** — Polar plot of satellite positions with constellation toggles
   - **Ephemeris** — Tabbed tables with orbital parameters and current azimuth/elevation per satellite
   - **Time Systems** — Current time displayed across all GNSS time references
5. **Export** — `File → Save Synthetic RINEX` (Ctrl+Shift+S) to write adjusted ephemerides to a new file

### Time Control

| Control | Action |
|---|---|
| `◁◁` | Large step backward (step × 6) |
| `◁` | Step backward |
| `▷` | Step forward |
| `▷▷` | Large step forward (step × 6) |
| `▶ / ■` | Play / Stop auto-advance |
| `Now` | Jump to current system time |
| Step spinner | Set step interval (1–60 minutes) |

## Project Structure

```
gnss-mon/
├── main.py                        # Entry point
├── requirements.txt
└── gnss_mon/
    ├── constants.py               # WGS-84, GM values, constellation config
    ├── core/
    │   ├── rinex_loader.py        # RINEX file parsing
    │   ├── rinex_writer.py        # Synthetic RINEX generation
    │   ├── ephemeris.py           # Ephemeris data structures and store
    │   ├── propagator.py          # Satellite position computation
    │   ├── coordinates.py         # Geodetic ↔ ECEF ↔ AzEl conversions
    │   └── time_systems.py        # GNSS time system conversions
    └── gui/
        ├── main_window.py         # Application window and orchestration
        ├── skyplot_tab.py         # Polar skyplot visualization
        ├── ephemeris_tab.py       # Ephemeris parameter tables
        ├── time_systems_tab.py    # Multi-system time display
        ├── time_control.py        # Time stepping and playback controls
        └── observer_dialog.py     # Observer position input dialog
```

## How It Works

1. **RINEX parsing** — `georinex` loads the navigation file; the loader extracts Keplerian orbital elements (GPS/Galileo/BeiDou) or state vectors (GLONASS) into an `EphemerisStore`
2. **Ephemeris lookup** — For each satellite at a given time, the store selects the closest valid ephemeris record
3. **Propagation** — Keplerian satellites are propagated using the IS-GPS-200 algorithm (Kepler's equation solved via Newton-Raphson, second harmonic corrections). GLONASS satellites use RK4 integration of the equations of motion including J2 perturbation and luni-solar acceleration
4. **Projection** — ECEF positions are transformed to azimuth/elevation relative to the observer via an ENU rotation matrix
5. **Visualization** — The skyplot renders satellites on a polar projection; ephemeris tables and time displays update on every time step

## License

GPL 3
