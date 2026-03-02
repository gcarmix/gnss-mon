"""Satellite position computation from broadcast ephemeris."""

import math
from datetime import datetime, timezone

import numpy as np

from gnss_mon.constants import (
    GM_GPS, GM_GAL, GM_BDS, GM_GLO,
    OMEGA_E, PI_GPS,
    GLO_AE, GLO_J2, GLO_OMEGA_E,
    CONSTELLATION_GPS, CONSTELLATION_GAL, CONSTELLATION_BDS, CONSTELLATION_GLO,
    GM,
)
from gnss_mon.core.ephemeris import KeplerianEphemeris, GlonassEphemeris
from gnss_mon.core.time_systems import GPS_EPOCH, SECONDS_PER_WEEK, TimeConverter


_tc = TimeConverter()


def _utc_to_gps_seconds(utc: datetime) -> float:
    """Total GPS seconds since GPS epoch."""
    gps = _tc.utc_to_gps(utc)
    dt = gps.replace(tzinfo=None) - GPS_EPOCH.replace(tzinfo=None)
    return dt.total_seconds()


def propagate_keplerian(eph: KeplerianEphemeris, utc: datetime) -> np.ndarray | None:
    """Compute ECEF position (meters) for GPS/Galileo/BeiDou satellite.

    Implements IS-GPS-200 Table 20-IV algorithm.
    Returns np.array([x, y, z]) or None if computation fails.
    """
    mu = GM.get(eph.constellation, GM_GPS)

    # Semi-major axis
    A = eph.sqrtA ** 2
    if A < 1e6:
        return None

    # Computed mean motion
    n0 = math.sqrt(mu / A ** 3)
    n = n0 + eph.DeltaN

    # Time from ephemeris reference epoch
    gps_sec = _utc_to_gps_seconds(utc)
    toe_sec = eph.week * SECONDS_PER_WEEK + eph.Toe
    tk = gps_sec - toe_sec

    # Account for week crossovers
    if tk > SECONDS_PER_WEEK / 2:
        tk -= SECONDS_PER_WEEK
    elif tk < -SECONDS_PER_WEEK / 2:
        tk += SECONDS_PER_WEEK

    # Mean anomaly
    Mk = eph.M0 + n * tk

    # Solve Kepler's equation by Newton-Raphson
    Ek = Mk
    for _ in range(10):
        dE = (Mk - Ek + eph.Eccentricity * math.sin(Ek)) / (1.0 - eph.Eccentricity * math.cos(Ek))
        Ek += dE
        if abs(dE) < 1e-12:
            break

    # True anomaly
    sin_Ek = math.sin(Ek)
    cos_Ek = math.cos(Ek)
    sin_vk = (math.sqrt(1.0 - eph.Eccentricity ** 2) * sin_Ek) / (1.0 - eph.Eccentricity * cos_Ek)
    cos_vk = (cos_Ek - eph.Eccentricity) / (1.0 - eph.Eccentricity * cos_Ek)
    vk = math.atan2(sin_vk, cos_vk)

    # Argument of latitude
    phi_k = vk + eph.omega

    # Second harmonic corrections
    sin_2phi = math.sin(2.0 * phi_k)
    cos_2phi = math.cos(2.0 * phi_k)

    du = eph.Cus * sin_2phi + eph.Cuc * cos_2phi
    dr = eph.Crs * sin_2phi + eph.Crc * cos_2phi
    di = eph.Cis * sin_2phi + eph.Cic * cos_2phi

    uk = phi_k + du
    rk = A * (1.0 - eph.Eccentricity * cos_Ek) + dr
    ik = eph.Io + di + eph.IDOT * tk

    # Positions in orbital plane
    xp = rk * math.cos(uk)
    yp = rk * math.sin(uk)

    # Corrected longitude of ascending node
    omega_k = eph.Omega0 + (eph.OmegaDot - OMEGA_E) * tk - OMEGA_E * eph.Toe

    # ECEF coordinates
    cos_omega = math.cos(omega_k)
    sin_omega = math.sin(omega_k)
    cos_ik = math.cos(ik)
    sin_ik = math.sin(ik)

    x = xp * cos_omega - yp * cos_ik * sin_omega
    y = xp * sin_omega + yp * cos_ik * cos_omega
    z = yp * sin_ik

    return np.array([x, y, z])


def _glonass_derivatives(state: np.ndarray, acc_luni_solar: np.ndarray) -> np.ndarray:
    """Compute derivatives for GLONASS equations of motion.

    state = [x, y, z, vx, vy, vz] in meters and m/s
    acc_luni_solar = [ax, ay, az] luni-solar acceleration in m/s^2
    """
    x, y, z, vx, vy, vz = state
    r = math.sqrt(x * x + y * y + z * z)
    if r < 1.0:
        return np.zeros(6)

    r2 = r * r
    r3 = r2 * r
    r5 = r2 * r3
    ae2 = GLO_AE * GLO_AE
    mu = GM_GLO
    we = GLO_OMEGA_E
    j2 = GLO_J2

    # Common factor for J2 perturbation
    c1 = -mu / r3
    c2 = 1.5 * j2 * mu * ae2 / r5

    z2_r2 = (z * z) / r2

    ax = c1 * x + c2 * x * (1.0 - 5.0 * z2_r2) + we * we * x + 2.0 * we * vy + acc_luni_solar[0]
    ay = c1 * y + c2 * y * (1.0 - 5.0 * z2_r2) + we * we * y - 2.0 * we * vx + acc_luni_solar[1]
    az = c1 * z + c2 * z * (3.0 - 5.0 * z2_r2) + acc_luni_solar[2]

    return np.array([vx, vy, vz, ax, ay, az])


def propagate_glonass(eph: GlonassEphemeris, utc: datetime) -> np.ndarray | None:
    """Compute ECEF position (meters) for GLONASS satellite via RK4 integration.

    Integrates from ephemeris epoch to target time in 60-second steps.
    Returns np.array([x, y, z]) or None.
    """
    dt_total = (utc.replace(tzinfo=None) - eph.epoch.replace(tzinfo=None)).total_seconds()

    state = np.array([eph.X, eph.Y, eph.Z, eph.dX, eph.dY, eph.dZ])
    acc = np.array([eph.dX2, eph.dY2, eph.dZ2])

    # Limit the number of RK4 iterations to avoid freezing the UI.
    # Use a 60-s step up to 4 h; beyond that, increase the step size so
    # the loop never exceeds ~240 iterations.  Accuracy degrades but we
    # still get a reasonable orbital guess.
    MAX_ITERS = 240
    abs_dt = abs(dt_total)
    step = max(60.0, abs_dt / MAX_ITERS)
    if dt_total < 0:
        step = -step

    t = 0.0
    remaining = abs_dt

    while remaining > 1e-9:
        h = step if remaining >= abs(step) else math.copysign(remaining, step)

        k1 = _glonass_derivatives(state, acc)
        k2 = _glonass_derivatives(state + 0.5 * h * k1, acc)
        k3 = _glonass_derivatives(state + 0.5 * h * k2, acc)
        k4 = _glonass_derivatives(state + h * k3, acc)

        state = state + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        remaining -= abs(h)

    return state[:3]


class SatellitePropagator:
    """Compute satellite positions from broadcast ephemeris."""

    def propagate(self, eph, utc: datetime) -> np.ndarray | None:
        if isinstance(eph, KeplerianEphemeris):
            return propagate_keplerian(eph, utc)
        elif isinstance(eph, GlonassEphemeris):
            return propagate_glonass(eph, utc)
        return None
