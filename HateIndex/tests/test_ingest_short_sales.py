"""Tests for the short-sales ingest helpers."""
from __future__ import annotations

from datetime import date

from scripts.ingest_short_sales import URL_TEMPLATE, business_days


def test_url_template_formats_yyyymmdd():
    url = URL_TEMPLATE.format(ymd="20260424")
    assert "RR20260424-001-SSDailyAggShortPos.csv" in url


def test_business_days_excludes_weekends():
    # 2026-04-25 = Saturday, 2026-04-26 = Sunday
    days = business_days(date(2026, 4, 24), date(2026, 4, 27))
    assert date(2026, 4, 24) in days   # Friday
    assert date(2026, 4, 25) not in days
    assert date(2026, 4, 26) not in days
    assert date(2026, 4, 27) in days   # Monday
    assert len(days) == 2


def test_business_days_inclusive_endpoints():
    days = business_days(date(2026, 4, 20), date(2026, 4, 24))  # Mon..Fri
    assert len(days) == 5
