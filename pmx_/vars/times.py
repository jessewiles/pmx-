from typing import Any, Dict

import moment  # type: ignore


def read_env_times() -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    result["tomorrowIsoMidnightUtc"] = (
        moment.now().add(days=1).format("YYYY-MM-DDT00:00:00-00:00")
    )
    result["TIME"] = moment.now().format("HHmmssSSS")
    result["TODAY"] = moment.now().format("YYYY-MM-DD")

    # These are the timezones, most of which are in Daylight Savings Time (DST)",
    result["AZ_TZ"] = "-0700"  # "Mountain Standard Time"
    result["CA_TZ"] = "-0700"  # "Pacific Daylight Time"
    result["NV_TZ"] = "-0700"  # "Pacific Daylight Time"
    result["CO_TZ"] = "-0600"  # "Mountain Daylight Time
    result["IL_TZ"] = "-0500"  # "Central Daylight Time"
    result["NC_TZ"] = "-0400"  # "Eastern Daylight Time"
    result["NJ_TZ"] = "-0400"  # "Eastern Daylight Time"
    result["NY_TZ"] = "-0400"  # "Eastern Daylight Time"
    result["OR_TZ"] = "-0700"  # "Pacific Daylight Time"
    result["PA_TZ"] = "-0400"  # "Eastern Daylight Time"
    result["VA_TZ"] = "-0400"  # "Eastern Daylight Time"

    today: moment.core.Moment = moment.now()
    result["TODAY_MIDNIGHT"] = today.format("YYYY-MM-DDT00:00:00")
    today_midnight_plus_1_year: moment.core.Moment = today.add(years=1)
    result["TODAY_MIDNIGHT_PLUS_1_YEAR"] = today_midnight_plus_1_year.format(
        "YYYY-MM-DDT00:00:00"
    )

    tomorrow = moment.now().add(days=1)
    result["TOMORROW"] = tomorrow.format("YYYY-MM-DDT00:00:00")

    tomorrow_plus_1_year = moment.now().add(days=1).add(years=1)
    result["TOMORROW_PLUS_1_YEAR"] = tomorrow_plus_1_year.format("YYYY-MM-DDT00:00:00")

    yesterday = moment.now().subtract(days=1)
    result["YESTERDAY"] = yesterday.format("YYYY-MM-DDT00:00:00")

    yesterday_plus_1_year = moment.now().subtract(days=1).add(years=1)
    result["YESTERDAY_PLUS_1_YEAR"] = yesterday_plus_1_year.format(
        "YYYY-MM-DDT00:00:00"
    )

    yesterday_plus_2_years = moment.now().subtract(days=1).add(years=2)
    result["YESTERDAY_PLUS_2_YEARS"] = yesterday_plus_2_years.format(
        "YYYY-MM-DDT00:00:00"
    )

    last_week = moment.now().subtract(days=7)
    result["LAST_WEEK"] = last_week.format("YYYY-MM-DDT00:00:00")

    six_days_ago = moment.now().subtract(days=6)
    result["SIX_DAYS_AGO"] = six_days_ago.format("YYYY-MM-DDT00:00:00")

    six_days_ago_plus_1_year = moment.now().subtract(days=6).add(years=1)
    result["SIX_DAYS_AGO_PLUS_1_YEAR"] = six_days_ago_plus_1_year.format(
        "YYYY-MM-DDT00:00:00"
    )

    next_week = moment.now().add(days=7)
    result["NEXT_WEEK"] = next_week.format("YYYY-MM-DDT00:00:00")

    next_week_minus_1_day = moment.now().add(days=6)
    result["NEXT_WEEK_MINUS_1_DAY"] = next_week_minus_1_day.format(
        "YYYY-MM-DDT00:00:00"
    )

    next_week_minus_1_year = moment.now().add(days=7).subtract(years=1)
    result["NEXT_WEEK_MINUS_1_YEAR"] = next_week_minus_1_year.format(
        "YYYY-MM-DDT00:00:00"
    )

    next_week_minus_2_years = moment.now().add(days=7).subtract(years=2)
    result["NEXT_WEEK_MINUS_2_YEARS"] = next_week_minus_2_years.format(
        "YYYY-MM-DDT00:00:00"
    )

    next_week_minus_3_years = moment.now().add(days=7).subtract(years=2)
    result["NEXT_WEEK_MINUS_3_YEARS"] = next_week_minus_3_years.format(
        "YYYY-MM-DDT00:00:00"
    )

    next_week_plus_1_day = moment.now().add(days=8)
    result["NEXT_WEEK_PLUS_1_DAY"] = next_week_plus_1_day.format("YYYY-MM-DDT00:00:00")

    next_week_plus_1_year = moment.now().add(days=7).add(years=1)
    result["NEXT_WEEK_PLUS_1_YEAR"] = next_week_plus_1_year.format(
        "YYYY-MM-DDT00:00:00"
    )

    next_week_plus_2_years = moment.now().add(days=7).add(years=2)
    result["NEXT_WEEK_PLUS_2_YEARS"] = next_week_plus_2_years.format(
        "YYYY-MM-DDT00:00:00"
    )

    two_weeks = moment.now().add(days=14)
    result["TWO_WEEKS"] = two_weeks.format("YYYY-MM-DDT00:00:00")

    two_weeks_plus_1_year = moment.now().add(days=14).add(years=1)
    result["TWO_WEEKS_PLUS_1_YEAR"] = two_weeks_plus_1_year.format(
        "YYYY-MM-DDT00:00:00"
    )

    twentyone_years_ago_datetime = moment.now().subtract(years=21)
    result["TWENTYONE_YEARS_AGO"] = twentyone_years_ago_datetime.format("YYYY-MM-DD")

    one_month_ago_datetime = moment.now().subtract(months=1)
    result["ONE_MONTH_AGO"] = one_month_ago_datetime.format("YYYY-MM-DD")

    two_months_ago_datetime = moment.now().subtract(months=2)
    result["TWO_MONTHS_AGO"] = two_months_ago_datetime.format("YYYY-MM-DD")

    return result
