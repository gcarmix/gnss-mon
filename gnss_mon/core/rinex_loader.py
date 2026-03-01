"""Load RINEX navigation files via georinex into EphemerisStore."""

import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import xarray as xr

from gnss_mon.constants import (
    RINEX_PREFIX, CONSTELLATION_GLO, CONSTELLATION_BDS,
    KEPLER_FIELDS, GLONASS_FIELDS,
)
from gnss_mon.core.ephemeris import KeplerianEphemeris, GlonassEphemeris, EphemerisStore


class RinexLoader:
    """Load RINEX 3 broadcast navigation files."""

    def load(self, filepath: str | Path) -> EphemerisStore:
        """Load a RINEX navigation file and return an EphemerisStore."""
        import georinex as gr

        filepath = Path(filepath)
        store = EphemerisStore()

        # Load each constellation separately. When georinex merges multiple
        # constellations into one xarray Dataset the different time grids
        # create a sparse outer-join matrix where values become NaN.
        for sys_char in ("G", "E", "R"):
            try:
                nav = gr.load(filepath, use={sys_char})
                if isinstance(nav, xr.Dataset) and "sv" in nav.coords:
                    self._extract(nav, store)
            except Exception:
                continue

        # BeiDou: georinex often returns all-NaN for BDS in RINEX 3.04,
        # so we use a direct text parser as fallback.
        try:
            nav = gr.load(filepath, use={"C"})
            if isinstance(nav, xr.Dataset) and "sv" in nav.coords:
                has_data = "sqrtA" in nav and np.any(~np.isnan(nav["sqrtA"].values))
                if has_data:
                    self._extract(nav, store)
                else:
                    self._parse_beidou_raw(filepath, store)
        except Exception:
            self._parse_beidou_raw(filepath, store)

        store.finalize()
        if len(store) == 0:
            raise ValueError(f"Could not parse any constellations from: {filepath}")
        return store

    def _extract(self, nav: xr.Dataset, store: EphemerisStore):
        """Extract ephemerides from an xarray Dataset into the store."""
        svs = nav.coords["sv"].values
        times = nav.coords["time"].values

        for sv_val in svs:
            sv_raw = str(sv_val)
            prefix = sv_raw[0]
            constellation = RINEX_PREFIX.get(prefix)
            if constellation is None:
                continue

            # Strip georinex suffixes like "_1" (e.g. "E02_1" for Galileo
            # dual-source I/NAV vs F/NAV records)
            sv = sv_raw[:3]

            for t_val in times:
                epoch = _numpy_to_datetime(t_val)

                if constellation == CONSTELLATION_GLO:
                    eph = self._load_glonass(nav, sv_raw, t_val, epoch, constellation)
                else:
                    eph = self._load_keplerian(nav, sv_raw, t_val, epoch, constellation)

                if eph is not None:
                    eph.sv = sv
                    store.add(eph)

    def _load_keplerian(self, nav: xr.Dataset, sv: str, time,
                        epoch: datetime, constellation: str) -> KeplerianEphemeris | None:
        try:
            sqrtA = _get_val(nav, "sqrtA", sv, time)
            if sqrtA is None or np.isnan(sqrtA) or sqrtA < 1000:
                return None

            eph = KeplerianEphemeris(sv=sv, constellation=constellation, epoch=epoch)
            for field in KEPLER_FIELDS:
                val = _get_val(nav, field, sv, time)
                if val is not None and not np.isnan(val):
                    setattr(eph, field, float(val))

            # Try to get week number
            week = _get_val(nav, "GPSWeek", sv, time)
            if week is None or np.isnan(week):
                week = _get_val(nav, "GALWeek", sv, time)
            if week is None or np.isnan(week):
                week = _get_val(nav, "BDTWeek", sv, time)
            if week is not None and not np.isnan(week):
                eph.week = int(week)

            return eph
        except (KeyError, ValueError):
            return None

    def _load_glonass(self, nav: xr.Dataset, sv: str, time,
                      epoch: datetime, constellation: str) -> GlonassEphemeris | None:
        try:
            x = _get_val(nav, "X", sv, time)
            if x is None or np.isnan(x):
                return None

            eph = GlonassEphemeris(sv=sv, constellation=constellation, epoch=epoch)

            # georinex provides GLONASS values in meters, m/s, and m/s^2
            for field in ("X", "Y", "Z", "dX", "dY", "dZ", "dX2", "dY2", "dZ2"):
                val = _get_val(nav, field, sv, time)
                if val is not None and not np.isnan(val):
                    setattr(eph, field, float(val))

            # Clock parameters (no unit conversion)
            for clk_field in ("SVclockBias", "SVclockDrift"):
                val = _get_val(nav, clk_field, sv, time)
                if val is not None and not np.isnan(val):
                    setattr(eph, clk_field, float(val))

            return eph
        except (KeyError, ValueError):
            return None

    def _parse_beidou_raw(self, filepath: Path, store: EphemerisStore):
        """Fallback: parse BeiDou ephemerides directly from RINEX 3 text.

        RINEX 3 BDS record: 8 lines per satellite (header + 7 data lines).
        Line 0: SV epoch clkBias clkDrift clkDriftRate
        Line 1: AODE Crs DeltaN M0
        Line 2: Cuc Eccentricity Cus sqrtA
        Line 3: Toe Cic Omega0 Cis
        Line 4: Io Crc omega OmegaDot
        Line 5: IDOT spare1 BDTWeek spare2
        Line 6: SatAcc SatH1 TGD1 TGD2
        Line 7: TransTime AODC
        """
        text = filepath.read_text(errors="ignore")
        lines = text.split("\n")

        # Skip header
        header_end = 0
        for i, line in enumerate(lines):
            if "END OF HEADER" in line:
                header_end = i + 1
                break

        i = header_end
        while i < len(lines):
            line = lines[i]
            if not line.startswith("C"):
                i += 1
                continue

            # Need 8 lines for a complete record
            if i + 7 >= len(lines):
                break

            try:
                record = lines[i:i + 8]
                eph = self._parse_bds_record(record)
                if eph is not None:
                    store.add(eph)
            except Exception:
                pass

            i += 8

    def _parse_bds_record(self, lines: list[str]) -> KeplerianEphemeris | None:
        """Parse a single BeiDou 8-line RINEX 3 record."""
        # Line 0: C05 2026 03 01 05 00 00-6.259197834879D-04 ...
        hdr = lines[0]
        sv = hdr[:3].strip()
        year = int(hdr[3:8])
        month = int(hdr[8:11])
        day = int(hdr[11:14])
        hour = int(hdr[14:17])
        minute = int(hdr[17:20])
        second = int(hdr[20:23])
        epoch = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

        vals0 = _parse_rinex_header_floats(hdr[23:])
        if len(vals0) < 3:
            return None

        # Parse data lines (4-space indent + 4 x 19-char fields per line)
        data = []
        for k in range(1, 8):
            data.extend(_parse_rinex_data_line(lines[k]))

        if len(data) < 25:
            return None

        eph = KeplerianEphemeris(sv=sv, constellation=CONSTELLATION_BDS, epoch=epoch)
        eph.SVclockBias = vals0[0]
        eph.SVclockDrift = vals0[1]
        eph.SVclockDriftRate = vals0[2]

        # Line 1: AODE Crs DeltaN M0
        eph.Crs = data[1]
        eph.DeltaN = data[2]
        eph.M0 = data[3]

        # Line 2: Cuc Eccentricity Cus sqrtA
        eph.Cuc = data[4]
        eph.Eccentricity = data[5]
        eph.Cus = data[6]
        eph.sqrtA = data[7]

        if eph.sqrtA < 1000:
            return None

        # Line 3: Toe Cic Omega0 Cis
        eph.Toe = data[8]
        eph.Cic = data[9]
        eph.Omega0 = data[10]
        eph.Cis = data[11]

        # Line 4: Io Crc omega OmegaDot
        eph.Io = data[12]
        eph.Crc = data[13]
        eph.omega = data[14]
        eph.OmegaDot = data[15]

        # Line 5: IDOT spare BDTWeek spare
        eph.IDOT = data[16]
        if len(data) > 18 and data[18] != 0:
            eph.week = int(data[18])

        # Line 7: TransTime ...
        if len(data) > 24:
            eph.TransTime = data[24]

        return eph


def _parse_rinex_data_line(s: str) -> list[float]:
    """Parse a RINEX 3 data line (4-space indent + up to 4 x 19-char fields)."""
    s = s.replace("D", "E").replace("d", "e")
    vals = []
    # Data lines: 4-char indent, then 19-char fixed-width fields
    for j in range(4, len(s), 19):
        chunk = s[j:j + 19].strip()
        if chunk:
            try:
                vals.append(float(chunk))
            except ValueError:
                vals.append(0.0)
        else:
            vals.append(0.0)
    return vals


def _parse_rinex_header_floats(s: str) -> list[float]:
    """Parse floats from the remainder of a RINEX record header line."""
    s = s.replace("D", "E").replace("d", "e")
    vals = []
    for j in range(0, len(s), 19):
        chunk = s[j:j + 19].strip()
        if chunk:
            try:
                vals.append(float(chunk))
            except ValueError:
                pass
    return vals


def _get_val(ds: xr.Dataset, var: str, sv: str, time):
    """Safely extract a scalar value from the xarray Dataset."""
    if var not in ds:
        return None
    try:
        val = ds[var].sel(sv=sv, time=time).values
        return float(val)
    except (KeyError, ValueError, TypeError):
        return None


def _numpy_to_datetime(np_time) -> datetime:
    """Convert numpy datetime64 to Python datetime."""
    ts = (np_time - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s")
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=float(ts))
