"""Date calculation utilities for file naming and pipeline execution."""

from datetime import date, datetime, timedelta
from typing import Tuple, Optional, Union
import logging

from utils.holiday_calendar import is_business_day, next_business_day, PDATE_COUNTRY

logger = logging.getLogger(__name__)


def _get_base_date(tday: Optional[str] = None) -> datetime:
    """
    Resolve the base 'today' date.

    If tday is provided (YYYY-MM-DD), use that; otherwise use datetime.today().
    """
    if tday:
        try:
            return datetime.strptime(tday, "%Y-%m-%d")
        except ValueError:
            logger.warning("Invalid tday '%s', falling back to system today()", tday)
    return datetime.today()


def calculate_next_tuesday(base_date: Optional[datetime] = None) -> str:
    """
    Calculate next Tuesday in YYYY-MM-DD format, adjusted for US business days.
    If that Tuesday is a US holiday (or weekend), returns the following US business day.
    """
    today = base_date or datetime.today()
    days_until_tuesday = (1 - today.weekday() + 7) % 7  # 1 is Tuesday
    days_until_tuesday = 7 if days_until_tuesday == 0 else days_until_tuesday
    candidate = today + timedelta(days=days_until_tuesday)
    candidate_date = candidate.date()
    if is_business_day(candidate_date, country=PDATE_COUNTRY):
        return candidate_date.strftime("%Y-%m-%d")
    # Tuesday is a US holiday or weekend; use next US business day
    next_bd = next_business_day(candidate_date, country=PDATE_COUNTRY, include_today=False)
    return next_bd.strftime("%Y-%m-%d")


def calculate_yesterday(base_date: Optional[datetime] = None) -> str:
    """Calculate yesterday's date in MM-DD-YYYY format."""
    today = base_date or datetime.today()
    yesterday = today - timedelta(days=1)
    return yesterday.strftime("%m-%d-%Y")


def calculate_last_month_end(base_date: Optional[datetime] = None) -> str:
    """
    Calculate last day of previous month in YYYY_MMM_DD format.
    Example: 2025_010_31 for January 31, 2025
    """
    today = base_date or datetime.today()
    first_day_of_current_month = datetime(today.year, today.month, 1)
    last_day_previous_month = first_day_of_current_month - timedelta(days=1)
    return f"{last_day_previous_month.year}_{last_day_previous_month.month:03}_{last_day_previous_month.day:02}"


def add_us_business_days(
    start: Union[date, datetime, str],
    n: int,
    fmt_in: str = "%Y-%m-%d",
    fmt_out: str = "%Y-%m-%d",
) -> str:
    """Add n US business days to start, skipping weekends and US federal holidays.

    Args:
        start: Start date (date, datetime, or string).
        n: Number of business days to add (must be >= 0).
        fmt_in: strptime format when start is a string (default YYYY-MM-DD).
        fmt_out: strftime format for the returned string (default YYYY-MM-DD).

    Returns:
        Resulting date as a string in fmt_out format.
    """
    if isinstance(start, str):
        d = datetime.strptime(start, fmt_in).date()
    elif isinstance(start, datetime):
        d = start.date()
    else:
        d = start

    count = 0
    while count < n:
        d += timedelta(days=1)
        if is_business_day(d, PDATE_COUNTRY):
            count += 1

    return d.strftime(fmt_out)


def calculate_pipeline_dates(pdate: str = None, tday: str = None) -> Tuple[str, str, str]:
    """
    Calculate all dates needed for pipeline execution.

    Args:
        pdate: Optional purchase date override (YYYY-MM-DD). If None, calculates next Tuesday.
        tday: Optional base date override (YYYY-MM-DD) for "today".
              When provided, yesterday/last_end are derived from this date, and the
              default pdate (when not passed) is the next Tuesday after this date.

    Returns:
        Tuple of (pdate, yesterday, last_end)
        - pdate: Purchase date in YYYY-MM-DD format
        - yesterday: Yesterday in MM-DD-YYYY format (for Tape20Loans files)
        - last_end: Last month end in YYYY_MMM_DD format (for FX files)
    """
    base_date = _get_base_date(tday)

    if pdate is None:
        pdate = calculate_next_tuesday(base_date=base_date)
    elif tday is None:
        # pdate was explicitly provided but tday was not — derive file dates from pdate
        # so that Tape20Loans date = pdate - 1 day (not system today - 1 day)
        base_date = datetime.strptime(pdate, "%Y-%m-%d")

    yesterday = calculate_yesterday(base_date=base_date)
    last_end = calculate_last_month_end(base_date=base_date)

    logger.info(f"Calculated dates - pdate: {pdate}, yesterday: {yesterday}, last_end: {last_end}")

    return pdate, yesterday, last_end
