"""GNSS time system conversions."""

from datetime import datetime, timedelta, timezone

from gnss_mon.constants import GPS_LEAP_SECONDS, BDS_GPS_OFFSET


# GPS epoch: January 6, 1980 00:00:00 UTC
GPS_EPOCH = datetime(1980, 1, 6, tzinfo=timezone.utc)

# BeiDou epoch: January 1, 2006 00:00:00 UTC
BDS_EPOCH = datetime(2006, 1, 1, tzinfo=timezone.utc)

SECONDS_PER_WEEK = 604800


class TimeConverter:
    """Convert between UTC and GNSS time systems."""

    def __init__(self, leap_seconds: int = GPS_LEAP_SECONDS):
        self.leap_seconds = leap_seconds

    def utc_to_gps(self, utc: datetime) -> datetime:
        """UTC -> GPS time (GPS is ahead of UTC by leap seconds)."""
        return utc + timedelta(seconds=self.leap_seconds)

    def gps_to_utc(self, gps: datetime) -> datetime:
        return gps - timedelta(seconds=self.leap_seconds)

    def utc_to_galileo(self, utc: datetime) -> datetime:
        """Galileo System Time = GPS time."""
        return self.utc_to_gps(utc)

    def utc_to_bdt(self, utc: datetime) -> datetime:
        """BeiDou Time = GPS time - 14 seconds."""
        return self.utc_to_gps(utc) - timedelta(seconds=BDS_GPS_OFFSET)

    def utc_to_glonass(self, utc: datetime) -> datetime:
        """GLONASS time = UTC + 3 hours (Moscow time, no leap seconds)."""
        return utc + timedelta(hours=3)

    def gps_week_tow(self, utc: datetime) -> tuple[int, float]:
        """Return (GPS week, time-of-week in seconds) for a UTC time."""
        gps_time = self.utc_to_gps(utc)
        dt = gps_time.replace(tzinfo=None) - GPS_EPOCH.replace(tzinfo=None)
        total_seconds = dt.total_seconds()
        week = int(total_seconds // SECONDS_PER_WEEK)
        tow = total_seconds - week * SECONDS_PER_WEEK
        return week, tow

    def bdt_week_tow(self, utc: datetime) -> tuple[int, float]:
        """Return (BDT week, time-of-week in seconds) for a UTC time."""
        bdt = self.utc_to_bdt(utc)
        dt = bdt.replace(tzinfo=None) - BDS_EPOCH.replace(tzinfo=None)
        total_seconds = dt.total_seconds()
        week = int(total_seconds // SECONDS_PER_WEEK)
        tow = total_seconds - week * SECONDS_PER_WEEK
        return week, tow

    def gal_week_tow(self, utc: datetime) -> tuple[int, float]:
        """Galileo uses GPS week numbering."""
        return self.gps_week_tow(utc)

    def format_all(self, utc: datetime) -> dict[str, str]:
        """Return formatted strings for all time systems."""
        gps = self.utc_to_gps(utc)
        gal = self.utc_to_galileo(utc)
        bdt = self.utc_to_bdt(utc)
        glo = self.utc_to_glonass(utc)

        gps_w, gps_tow = self.gps_week_tow(utc)
        gal_w, gal_tow = self.gal_week_tow(utc)
        bdt_w, bdt_tow = self.bdt_week_tow(utc)

        fmt = "%Y-%m-%d %H:%M:%S"
        return {
            "UTC": utc.strftime(fmt),
            "GPST": f"{gps.strftime(fmt)}  (Week {gps_w}, ToW {gps_tow:.0f}s)",
            "GST": f"{gal.strftime(fmt)}  (Week {gal_w}, ToW {gal_tow:.0f}s)",
            "BDT": f"{bdt.strftime(fmt)}  (Week {bdt_w}, ToW {bdt_tow:.0f}s)",
            "GLONASST": f"{glo.strftime(fmt)}  (Moscow time)",
        }
