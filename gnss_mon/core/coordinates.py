"""Coordinate transformations: geodetic <-> ECEF, azimuth/elevation."""

import math

import numpy as np

from gnss_mon.constants import WGS84_A, WGS84_E2


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt: float = 0.0) -> np.ndarray:
    """Convert geodetic coordinates (degrees, meters) to ECEF (meters)."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    N = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat ** 2)

    x = (N + alt) * cos_lat * cos_lon
    y = (N + alt) * cos_lat * sin_lon
    z = (N * (1.0 - WGS84_E2) + alt) * sin_lat

    return np.array([x, y, z])


def ecef_to_azel(observer_ecef: np.ndarray, sat_ecef: np.ndarray,
                 lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Compute azimuth and elevation (degrees) from observer to satellite.

    Returns (azimuth, elevation) in degrees. Azimuth is clockwise from North.
    """
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)

    dx = sat_ecef - observer_ecef

    # Rotation matrix ECEF -> ENU
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    R = np.array([
        [-sin_lon, cos_lon, 0.0],
        [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
        [cos_lat * cos_lon, cos_lat * sin_lon, sin_lat],
    ])

    enu = R @ dx
    e, n, u = enu[0], enu[1], enu[2]

    horiz = math.sqrt(e ** 2 + n ** 2)
    elevation = math.degrees(math.atan2(u, horiz))
    azimuth = math.degrees(math.atan2(e, n)) % 360.0

    return azimuth, elevation
