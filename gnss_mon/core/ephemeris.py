"""Ephemeris dataclasses and EphemerisStore container."""

from dataclasses import dataclass, fields
from datetime import datetime
from typing import Optional

import numpy as np


@dataclass
class KeplerianEphemeris:
    """Keplerian broadcast ephemeris for GPS, Galileo, and BeiDou."""

    sv: str  # e.g. "G01", "E05", "C12"
    constellation: str
    epoch: datetime  # time of clock (toc)

    sqrtA: float = 0.0
    Eccentricity: float = 0.0
    M0: float = 0.0
    omega: float = 0.0  # argument of perigee
    Omega0: float = 0.0  # longitude of ascending node
    Io: float = 0.0  # inclination
    DeltaN: float = 0.0
    IDOT: float = 0.0
    OmegaDot: float = 0.0
    Cus: float = 0.0
    Cuc: float = 0.0
    Crs: float = 0.0
    Crc: float = 0.0
    Cis: float = 0.0
    Cic: float = 0.0
    Toe: float = 0.0  # time of ephemeris (seconds of week)
    TransTime: float = 0.0
    SVclockBias: float = 0.0
    SVclockDrift: float = 0.0
    SVclockDriftRate: float = 0.0
    week: int = 0


@dataclass
class GlonassEphemeris:
    """GLONASS broadcast ephemeris (state vectors in meters)."""

    sv: str  # e.g. "R01"
    constellation: str
    epoch: datetime

    X: float = 0.0  # position (m)
    Y: float = 0.0
    Z: float = 0.0
    dX: float = 0.0  # velocity (m/s)
    dY: float = 0.0
    dZ: float = 0.0
    dX2: float = 0.0  # luni-solar acceleration (m/s^2)
    dY2: float = 0.0
    dZ2: float = 0.0
    SVclockBias: float = 0.0
    SVclockDrift: float = 0.0


class EphemerisStore:
    """Container for satellite ephemerides with closest-epoch lookup."""

    def __init__(self):
        self._data: dict[str, list] = {}  # sv -> list of ephemeris objects
        self.time_span: tuple[Optional[datetime], Optional[datetime]] = (None, None)

    def clear(self):
        self._data.clear()
        self.time_span = (None, None)

    def add(self, eph):
        sv = eph.sv
        if sv not in self._data:
            self._data[sv] = []
        self._data[sv].append(eph)

    def finalize(self):
        """Sort ephemerides by epoch, deduplicate, and compute time span.

        Removes duplicate epochs per SV (keeps last occurrence — e.g.
        Galileo I/NAV vs F/NAV duplicates).
        Uses the 10th/90th percentile of epochs to avoid stale outlier
        timestamps skewing the range (common in mixed RINEX files).
        """
        all_epochs = []
        for sv in self._data:
            self._data[sv].sort(key=lambda e: e.epoch)
            # Deduplicate: keep last entry per epoch (truncated to seconds
            # to catch floating-point differences from numpy conversion;
            # also catches Galileo I/NAV vs F/NAV dual-source records)
            seen = {}
            for e in self._data[sv]:
                key = e.epoch.replace(microsecond=0)
                seen[key] = e
            self._data[sv] = list(seen.values())
            for e in self._data[sv]:
                all_epochs.append(e.epoch)
        if all_epochs:
            all_epochs.sort()
            # Use percentile-based range to ignore stale outlier epochs
            n = len(all_epochs)
            lo = all_epochs[max(0, n // 10)]
            hi = all_epochs[min(n - 1, n - 1 - n // 10)]
            self.time_span = (lo, hi)

    def get_satellites(self) -> list[str]:
        return sorted(self._data.keys())

    def get_constellation_satellites(self, constellation: str) -> list[str]:
        from gnss_mon.constants import RINEX_PREFIX
        prefix_map = {v: k for k, v in RINEX_PREFIX.items()}
        prefix = prefix_map.get(constellation, "")
        return sorted(sv for sv in self._data if sv.startswith(prefix))

    def get_closest(self, sv: str, t: datetime):
        """Return the ephemeris closest in time to t for the given SV."""
        entries = self._data.get(sv, [])
        if not entries:
            return None
        best = min(entries, key=lambda e: abs((e.epoch - t).total_seconds()))
        return best

    def get_latest(self, sv: str):
        """Return the most recent ephemeris for the given SV."""
        entries = self._data.get(sv, [])
        if not entries:
            return None
        return entries[-1]  # sorted by epoch in finalize()

    def __len__(self):
        return sum(len(v) for v in self._data.values())
