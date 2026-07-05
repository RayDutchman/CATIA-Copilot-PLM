from fastapi import APIRouter

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/timezones")
@router.get("/timezones/", include_in_schema=False)
def list_timezones():
    try:
        from zoneinfo import available_timezones
        return sorted(available_timezones())
    except ImportError:
        return sorted([
            "UTC",
            "Africa/Cairo",
            "Africa/Johannesburg",
            "Africa/Lagos",
            "Africa/Nairobi",
            "America/Argentina/Buenos_Aires",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "America/Mexico_City",
            "America/New_York",
            "America/Sao_Paulo",
            "America/Toronto",
            "Asia/Bangkok",
            "Asia/Dubai",
            "Asia/Hong_Kong",
            "Asia/Jerusalem",
            "Asia/Kolkata",
            "Asia/Seoul",
            "Asia/Shanghai",
            "Asia/Singapore",
            "Asia/Tokyo",
            "Australia/Sydney",
            "Europe/Berlin",
            "Europe/Istanbul",
            "Europe/London",
            "Europe/Moscow",
            "Europe/Paris",
            "Pacific/Auckland",
            "Pacific/Fiji",
            "Pacific/Honolulu",
        ])
