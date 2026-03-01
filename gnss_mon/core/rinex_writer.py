"""Write synthetic RINEX 3 navigation files."""

import math
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from gnss_mon.constants import (
    GM, GM_GPS, OMEGA_E,
    CONSTELLATION_GPS, CONSTELLATION_GAL, CONSTELLATION_BDS, CONSTELLATION_GLO,
)
from gnss_mon.core.ephemeris import KeplerianEphemeris, GlonassEphemeris, EphemerisStore
from gnss_mon.core.propagator import propagate_glonass, _glonass_derivatives
from gnss_mon.core.time_systems import SECONDS_PER_WEEK


def _broadcast_slot(sim_time: datetime, constellation: str) -> datetime:
    """Return the broadcast slot at or before sim_time for the constellation."""
    t = sim_time.replace(second=0, microsecond=0, tzinfo=timezone.utc)
    if constellation == CONSTELLATION_GPS:
        # Even 2-hour boundaries
        t = t.replace(minute=0)
        t = t.replace(hour=(t.hour // 2) * 2)
    elif constellation == CONSTELLATION_GAL:
        # 10-minute boundaries
        t = t.replace(minute=(t.minute // 10) * 10)
    elif constellation == CONSTELLATION_BDS:
        # 1-hour boundaries
        t = t.replace(minute=0)
    elif constellation == CONSTELLATION_GLO:
        # 30-minute boundaries
        t = t.replace(minute=(t.minute // 30) * 30)
    return t


def _adjust_keplerian(eph: KeplerianEphemeris, sim_time: datetime) -> KeplerianEphemeris:
    """Create a new ephemeris adjusted to the broadcast slot of sim_time."""
    new = deepcopy(eph)
    new_toc = _broadcast_slot(sim_time, eph.constellation)
    new.epoch = new_toc

    dt = (new_toc.replace(tzinfo=None) - eph.epoch.replace(tzinfo=None)).total_seconds()
    if dt == 0:
        return new

    mu = GM.get(eph.constellation, GM_GPS)
    A = eph.sqrtA ** 2
    if A < 1e6:
        return new

    n0 = math.sqrt(mu / A ** 3)
    n = n0 + eph.DeltaN

    # Propagate mean anomaly
    new.M0 = eph.M0 + n * dt

    # Propagate RAAN
    new.Omega0 = eph.Omega0 + eph.OmegaDot * dt

    # Adjust Toe
    new.Toe = eph.Toe + dt
    # Handle week crossover
    while new.Toe >= SECONDS_PER_WEEK:
        new.Toe -= SECONDS_PER_WEEK
        new.week += 1
    while new.Toe < 0:
        new.Toe += SECONDS_PER_WEEK
        new.week -= 1

    # Adjust TransTime similarly
    new.TransTime = eph.TransTime + dt

    return new


def _adjust_glonass(eph: GlonassEphemeris, sim_time: datetime) -> GlonassEphemeris:
    """Propagate GLONASS state vector to the broadcast slot of sim_time."""
    new = deepcopy(eph)
    new_epoch = _broadcast_slot(sim_time, CONSTELLATION_GLO)
    new.epoch = new_epoch

    dt_total = (new_epoch.replace(tzinfo=None) - eph.epoch.replace(tzinfo=None)).total_seconds()
    if abs(dt_total) < 1e-9:
        return new

    # RK4 integration (same as propagator but we keep velocity too)
    state = np.array([eph.X, eph.Y, eph.Z, eph.dX, eph.dY, eph.dZ])
    acc = np.array([eph.dX2, eph.dY2, eph.dZ2])

    step = 60.0
    if dt_total < 0:
        step = -step

    remaining = abs(dt_total)
    while remaining > 1e-9:
        h = step if remaining >= abs(step) else math.copysign(remaining, step)
        k1 = _glonass_derivatives(state, acc)
        k2 = _glonass_derivatives(state + 0.5 * h * k1, acc)
        k3 = _glonass_derivatives(state + 0.5 * h * k2, acc)
        k4 = _glonass_derivatives(state + h * k3, acc)
        state = state + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        remaining -= abs(h)

    new.X, new.Y, new.Z = state[0], state[1], state[2]
    new.dX, new.dY, new.dZ = state[3], state[4], state[5]
    return new


def _fmt(val: float) -> str:
    """Format a float as a 19-char RINEX field with D exponent notation."""
    s = f"{val: .12E}"
    s = s.replace("E", "D")
    return s.rjust(19)


def _epoch_str(dt: datetime) -> str:
    """Format epoch as 'YYYY MM DD HH MM SS'."""
    return f"{dt.year:4d} {dt.month:02d} {dt.day:02d} {dt.hour:02d} {dt.minute:02d} {dt.second:02d}"


class RinexWriter:
    """Write a synthetic RINEX 3 navigation file."""

    def write(self, store: EphemerisStore, sim_time: datetime, filepath: str | Path):
        filepath = Path(filepath)
        now = datetime.now(timezone.utc)
        lines = []

        # Header
        lines.append(
            f"     3.04           N: GNSS NAV DATA    M: MIXED            "
            f"RINEX VERSION / TYPE"
        )
        lines.append(
            f"GNSS-MON SYNTH      synthetic           "
            f"{now.strftime('%Y%m%d %H%M%S')} UTC "
            f"PGM / RUN BY / DATE"
        )
        lines.append(
            f"    18    18  1929     7"
            f"{' ' * 36}"
            f"LEAP SECONDS"
        )
        lines.append(
            f"{' ' * 60}"
            f"END OF HEADER"
        )

        # Collect adjusted ephemerides
        records = []
        for sv in store.get_satellites():
            eph = self._pick_eph(store, sv, sim_time)
            if eph is None:
                continue
            if isinstance(eph, KeplerianEphemeris):
                adjusted = _adjust_keplerian(eph, sim_time)
                records.append(adjusted)
            elif isinstance(eph, GlonassEphemeris):
                adjusted = _adjust_glonass(eph, sim_time)
                records.append(adjusted)

        # Sort by SV name for clean output
        records.sort(key=lambda e: e.sv)

        for eph in records:
            if isinstance(eph, KeplerianEphemeris):
                lines.extend(self._format_keplerian(eph))
            elif isinstance(eph, GlonassEphemeris):
                lines.extend(self._format_glonass(eph))

        filepath.write_text("\n".join(lines) + "\n")

    def _pick_eph(self, store: EphemerisStore, sv: str, sim_time: datetime):
        """Pick the most recent ephemeris at or before sim_time, or closest."""
        entries = store._data.get(sv, [])
        if not entries:
            return None
        # Find entries at or before sim_time
        before = [e for e in entries if e.epoch <= sim_time]
        if before:
            return before[-1]  # already sorted by epoch
        # Fallback: closest
        return min(entries, key=lambda e: abs((e.epoch - sim_time).total_seconds()))

    def _format_keplerian(self, eph: KeplerianEphemeris) -> list[str]:
        """Format a Keplerian ephemeris as 8 RINEX lines."""
        sv = eph.sv.ljust(3)
        ep = _epoch_str(eph.epoch)
        indent = "    "

        line0 = f"{sv} {ep}{_fmt(eph.SVclockBias)}{_fmt(eph.SVclockDrift)}{_fmt(eph.SVclockDriftRate)}"

        # Line 1: IODE/AODE Crs DeltaN M0
        line1 = f"{indent}{_fmt(0.0)}{_fmt(eph.Crs)}{_fmt(eph.DeltaN)}{_fmt(eph.M0)}"

        # Line 2: Cuc Eccentricity Cus sqrtA
        line2 = f"{indent}{_fmt(eph.Cuc)}{_fmt(eph.Eccentricity)}{_fmt(eph.Cus)}{_fmt(eph.sqrtA)}"

        # Line 3: Toe Cic Omega0 Cis
        line3 = f"{indent}{_fmt(eph.Toe)}{_fmt(eph.Cic)}{_fmt(eph.Omega0)}{_fmt(eph.Cis)}"

        # Line 4: Io Crc omega OmegaDot
        line4 = f"{indent}{_fmt(eph.Io)}{_fmt(eph.Crc)}{_fmt(eph.omega)}{_fmt(eph.OmegaDot)}"

        # Line 5: IDOT CodesL2/DataSrc Week L2PFlag/spare
        line5 = f"{indent}{_fmt(eph.IDOT)}{_fmt(0.0)}{_fmt(float(eph.week))}{_fmt(0.0)}"

        # Line 6: Accuracy Health TGD IODC/spare
        line6 = f"{indent}{_fmt(0.0)}{_fmt(0.0)}{_fmt(0.0)}{_fmt(0.0)}"

        # Line 7: TransTime FitInterval/AODC
        line7 = f"{indent}{_fmt(eph.TransTime)}{_fmt(0.0)}"

        return [line0, line1, line2, line3, line4, line5, line6, line7]

    def _format_glonass(self, eph: GlonassEphemeris) -> list[str]:
        """Format a GLONASS ephemeris as 4 RINEX lines."""
        sv = eph.sv.ljust(3)
        ep = _epoch_str(eph.epoch)
        indent = "    "

        # Positions in km for RINEX, velocities in km/s, accelerations in km/s^2
        x_km = eph.X / 1000.0
        y_km = eph.Y / 1000.0
        z_km = eph.Z / 1000.0
        dx_km = eph.dX / 1000.0
        dy_km = eph.dY / 1000.0
        dz_km = eph.dZ / 1000.0
        dx2_km = eph.dX2 / 1000.0
        dy2_km = eph.dY2 / 1000.0
        dz2_km = eph.dZ2 / 1000.0

        # Line 0: SV epoch clkBias relFreqBias msgFrameTime
        line0 = f"{sv} {ep}{_fmt(eph.SVclockBias)}{_fmt(eph.SVclockDrift)}{_fmt(0.0)}"

        # Line 1: X dX dX2 health
        line1 = f"{indent}{_fmt(x_km)}{_fmt(dx_km)}{_fmt(dx2_km)}{_fmt(0.0)}"

        # Line 2: Y dY dY2 freqNum
        line2 = f"{indent}{_fmt(y_km)}{_fmt(dy_km)}{_fmt(dy2_km)}{_fmt(0.0)}"

        # Line 3: Z dZ dZ2 ageOpInfo
        line3 = f"{indent}{_fmt(z_km)}{_fmt(dz_km)}{_fmt(dz2_km)}{_fmt(0.0)}"

        return [line0, line1, line2, line3]
