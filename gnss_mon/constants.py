"""WGS-84 constants, gravitational parameters, constellation colors, and field mappings."""

import math

# WGS-84 ellipsoid
WGS84_A = 6378137.0  # semi-major axis (m)
WGS84_F = 1.0 / 298.257223563  # flattening
WGS84_B = WGS84_A * (1.0 - WGS84_F)  # semi-minor axis
WGS84_E2 = 2.0 * WGS84_F - WGS84_F ** 2  # first eccentricity squared
OMEGA_E = 7.2921151467e-5  # Earth rotation rate (rad/s)

# Gravitational parameters (m^3/s^2)
GM_GPS = 3.986005e14
GM_GAL = 3.986004418e14
GM_BDS = 3.986004418e14
GM_GLO = 3.9860044e14

# GLONASS specific
GLO_AE = 6378136.0  # Earth equatorial radius (m)
GLO_J2 = 1.0826257e-3  # J2 zonal harmonic
GLO_OMEGA_E = 7.2921151467e-5  # Earth rotation rate (rad/s)

# Speed of light
C_LIGHT = 299792458.0

# Pi (use GPS ICD value for consistency)
PI_GPS = 3.1415926535898

# Constellation identifiers
CONSTELLATION_GPS = "GPS"
CONSTELLATION_GAL = "Galileo"
CONSTELLATION_GLO = "GLONASS"
CONSTELLATION_BDS = "BeiDou"

# Constellation prefixes in RINEX
RINEX_PREFIX = {
    "G": CONSTELLATION_GPS,
    "E": CONSTELLATION_GAL,
    "R": CONSTELLATION_GLO,
    "C": CONSTELLATION_BDS,
}

# Colors for skyplot (bright for dark background)
CONSTELLATION_COLORS = {
    CONSTELLATION_GPS: "#89b4fa",      # blue
    CONSTELLATION_GAL: "#fab387",      # peach
    CONSTELLATION_GLO: "#f38ba8",      # red
    CONSTELLATION_BDS: "#a6e3a1",      # green
}

# GM per constellation
GM = {
    CONSTELLATION_GPS: GM_GPS,
    CONSTELLATION_GAL: GM_GAL,
    CONSTELLATION_BDS: GM_BDS,
    CONSTELLATION_GLO: GM_GLO,
}

# georinex field name mappings for Keplerian ephemerides (GPS/GAL/BDS)
KEPLER_FIELDS = {
    "sqrtA": "sqrtA",
    "Eccentricity": "Eccentricity",
    "M0": "M0",
    "omega": "omega",
    "Omega0": "Omega0",
    "Io": "Io",
    "DeltaN": "DeltaN",
    "IDOT": "IDOT",
    "OmegaDot": "OmegaDot",
    "Cus": "Cus",
    "Cuc": "Cuc",
    "Crs": "Crs",
    "Crc": "Crc",
    "Cis": "Cis",
    "Cic": "Cic",
    "Toe": "Toe",
    "TransTime": "TransTime",
    "SVclockBias": "SVclockBias",
    "SVclockDrift": "SVclockDrift",
    "SVclockDriftRate": "SVclockDriftRate",
}

# georinex field name mappings for GLONASS ephemerides
GLONASS_FIELDS = {
    "X": "X",
    "Y": "Y",
    "Z": "Z",
    "dX": "dX",
    "dY": "dY",
    "dZ": "dZ",
    "dX2": "dX2",
    "dY2": "dY2",
    "dZ2": "dZ2",
    "SVclockBias": "SVclockBias",
    "SVclockDrift": "SVclockDrift",
}

# GPS epoch
GPS_EPOCH_YEAR = 1980
GPS_EPOCH_MONTH = 1
GPS_EPOCH_DAY = 6

# Leap seconds (GPS-UTC) as of 2017-01-01
GPS_LEAP_SECONDS = 18

# BeiDou epoch offset from GPS (BDT = GPST - 14s)
BDS_GPS_OFFSET = 14
