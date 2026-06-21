"""Octopus Greener Nights forecast fetch, carbon intensity, and dashboard payload."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .octopus_api import OctopusApiClient, OctopusApiError
from .octopus_graphql import OctopusGraphqlClient, OctopusGraphqlError

_LOGGER = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")
GREEN_THRESHOLD_GCO2 = 99.0
CARBON_SCORE_BASE = 60.0
CARBON_SCORE_SCALE = 25.0


def octopus_tariff_enabled(tariff: Any) -> bool:
    """True when Octopus is selected as the dynamic tariff provider."""
    from .octopus_tariff import OCTOPUS_PROVIDER

    dyn = getattr(tariff, "dynamic", None)
    if dyn is None:
        return False
    return bool(getattr(dyn, "enabled", False) and getattr(dyn, "provider", "") == OCTOPUS_PROVIDER)


def account_postcode(account: dict[str, Any]) -> str | None:
    for prop in account.get("properties") or []:
        if not isinstance(prop, dict):
            continue
        pc = prop.get("postcode")
        if pc:
            return str(pc).strip()
    for key in ("billing_postcode", "billingAddressPostcode"):
        raw = account.get(key)
        if raw:
            return str(raw).strip()
    return None


def low_carbon_score_from_gco2(value: float | None) -> int | None:
    if value is None:
        return None
    try:
        gco2 = float(value)
    except (TypeError, ValueError):
        return None
    score = round(10 - (gco2 - CARBON_SCORE_BASE) / CARBON_SCORE_SCALE)
    return max(1, min(10, score))


def _parse_period_start(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dt_util.parse_datetime(str(raw))
    except (TypeError, ValueError):
        dt = None
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UK_TZ)
    return dt.astimezone(UK_TZ)


def normalize_carbon_periods(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        start = _parse_period_start(row.get("periodStart"))
        if start is None:
            continue
        end = start + timedelta(minutes=30)
        try:
            gco2 = float(row.get("value"))
        except (TypeError, ValueError):
            gco2 = None
        score = low_carbon_score_from_gco2(gco2)
        out.append(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "start_ms": int(start.timestamp() * 1000),
                "end_ms": int(end.timestamp() * 1000),
                "gco2_per_kwh": gco2,
                "low_carbon_score": score,
                "index": row.get("index"),
                "is_green": gco2 is not None and gco2 < GREEN_THRESHOLD_GCO2,
            }
        )
    out.sort(key=lambda item: item["start_ms"])
    return out


def normalize_greener_nights(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        raw_date = row.get("date")
        if not raw_date:
            continue
        try:
            score = int(row.get("greennessScore"))
        except (TypeError, ValueError):
            score = None
        out.append(
            {
                "date": str(raw_date),
                "greenness_score": score,
                "greenness_index": row.get("greennessIndex"),
                "is_greener_night": bool(row.get("isGreenerNight")),
            }
        )
    out.sort(key=lambda item: item["date"])
    return out


def _find_green_window(periods: list[dict[str, Any]], *, now_ms: int) -> dict[str, Any]:
    future = [p for p in periods if p["end_ms"] > now_ms]
    if not future:
        return {}
    green = [p for p in future if p.get("is_green")]
    if not green:
        return {"next_green_start_ms": None, "next_green_end_ms": None}
    start_ms = green[0]["start_ms"]
    end_ms = green[0]["end_ms"]
    for period in green[1:]:
        if period["start_ms"] <= end_ms + 60_000:
            end_ms = max(end_ms, period["end_ms"])
        else:
            break
    return {"next_green_start_ms": start_ms, "next_green_end_ms": end_ms}


def build_greener_timeline(
    periods: list[dict[str, Any]],
    greener_nights: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> list[dict[str, str]]:
    """Human-readable timeline entries for the card."""
    now_dt = now or dt_util.now(UK_TZ)
    now_ms = int(now_dt.timestamp() * 1000)
    entries: list[dict[str, str]] = []

    window = _find_green_window(periods, now_ms=now_ms)
    green_start = window.get("next_green_start_ms")
    green_end = window.get("next_green_end_ms")

    if green_start and green_end and green_start > now_ms:
        start_dt = datetime.fromtimestamp(green_start / 1000, tz=UK_TZ)
        end_dt = datetime.fromtimestamp(green_end / 1000, tz=UK_TZ)
        ref_day = now_dt.date()
        start_label = _fmt_ampm(start_dt, ref=ref_day)
        end_label = _fmt_ampm(end_dt, ref=ref_day)
        entries.append(
            {
                "tone": "warn",
                "title": f"Until {start_label}: try to reduce or shift usage",
                "detail": "Consider waiting for cleaner grid periods if you can.",
            }
        )
        entries.append(
            {
                "tone": "good",
                "title": f"From {start_label} to {end_label}: good time to run appliances",
                "detail": (
                    "Great time to run your dishwasher, washing machine, or charge devices."
                ),
            }
        )
        entries.append(
            {
                "tone": "warn",
                "title": f"After {end_label}: try to reduce or shift usage",
                "detail": "",
            }
        )
        return entries

    tonight = _tonight_greener_night(greener_nights, now_dt.date())
    if tonight:
        score = tonight.get("greenness_score")
        if tonight.get("is_greener_night"):
            entries.append(
                {
                    "tone": "good",
                    "title": (
                        f"Tonight is forecast as a greener night"
                        f"{f' (score {score}/100)' if score is not None else ''}"
                    ),
                    "detail": "Good window for overnight EV charging or flexible loads (23:00–06:00).",
                }
            )
        else:
            entries.append(
                {
                    "tone": "warn",
                    "title": (
                        f"Tonight is not flagged as a greener night"
                        f"{f' (score {score}/100)' if score is not None else ''}"
                    ),
                    "detail": "Shift discretionary usage if a greener night is coming up.",
                }
            )
    upcoming = [n for n in greener_nights if n.get("is_greener_night")]
    if upcoming:
        next_night = upcoming[0]
        entries.append(
            {
                "tone": "good",
                "title": (
                    f"Next greener night: {next_night.get('date')} "
                    f"({next_night.get('greenness_score', '—')}/100)"
                ),
                "detail": "",
            }
        )
    if not entries:
        entries.append(
            {
                "tone": "neutral",
                "title": "Greener nights forecast updates daily",
                "detail": "Check back for the next overnight window.",
            }
        )
    return entries


def _tonight_greener_night(greener_nights: list[dict[str, Any]], today: date) -> dict[str, Any] | None:
    """Map calendar today to greener night row (00:00–06:00 window uses today's date)."""
    key = today.isoformat()
    for row in greener_nights:
        if row.get("date") == key:
            return row
    return greener_nights[0] if greener_nights else None


def _fmt_ampm(dt: datetime, *, ref: date | None = None) -> str:
    ref = ref or dt_util.now(UK_TZ).date()
    if dt.date() > ref:
        day_hint = " tomorrow"
    elif dt.date() < ref:
        day_hint = " yesterday"
    else:
        day_hint = ""
    hour = dt.hour % 12 or 12
    suffix = "am" if dt.hour < 12 else "pm"
    return f"{hour}{suffix}{day_hint}"


def greener_card_title(periods: list[dict[str, Any]], *, now: datetime | None = None) -> str:
    now_dt = now or dt_util.now(UK_TZ)
    now_ms = int(now_dt.timestamp() * 1000)
    window = _find_green_window(periods, now_ms=now_ms)
    start_ms = window.get("next_green_start_ms")
    if start_ms:
        start_dt = datetime.fromtimestamp(start_ms / 1000, tz=UK_TZ)
        if start_ms <= now_ms:
            return "Clean energy now"
        return f"Clean energy from {_fmt_ampm(start_dt).upper()}"
    return "Octopus Greener Nights"


async def fetch_octopus_greener_snapshot(
    hass: Any,
    *,
    api_key: str | None,
    account_number: str | None,
) -> dict[str, Any]:
    """Fetch greener nights (public) and optional carbon/rewards (authenticated)."""
    gql = OctopusGraphqlClient(hass, api_key=api_key)
    snapshot: dict[str, Any] = {
        "fetched_at": dt_util.utcnow().isoformat(),
        "greener_nights": [],
        "carbon_periods": [],
        "postcode": None,
        "rewards": None,
        "errors": {},
    }
    try:
        snapshot["greener_nights"] = normalize_greener_nights(
            await gql.fetch_greener_nights_forecast()
        )
    except OctopusGraphqlError as err:
        snapshot["errors"]["greener_nights"] = str(err)
        _LOGGER.warning("Greener nights fetch failed: %s", err)

    if not api_key or not account_number:
        return snapshot

    postcode: str | None = None
    try:
        rest = OctopusApiClient(hass, api_key=api_key)
        account = await rest.get_account(account_number)
        postcode = account_postcode(account)
        snapshot["postcode"] = postcode
    except OctopusApiError as err:
        snapshot["errors"]["account"] = str(err)

    if postcode:
        try:
            snapshot["carbon_periods"] = normalize_carbon_periods(
                await gql.fetch_carbon_intensity(postcode)
            )
        except OctopusGraphqlError as err:
            snapshot["errors"]["carbon"] = str(err)
            _LOGGER.debug("Carbon intensity fetch failed: %s", err)

    try:
        snapshot["rewards"] = await gql.fetch_rewards(account_number)
    except OctopusGraphqlError as err:
        snapshot["errors"]["rewards"] = str(err)
        _LOGGER.debug("Octopus rewards fetch failed: %s", err)

    return snapshot


def greener_dashboard_payload(
    snapshot: dict[str, Any] | None,
    *,
    history_count: int = 0,
    current_import_p_per_kwh: float | None = None,
) -> dict[str, Any]:
    """Panel-friendly greener nights + rewards payload."""
    snap = snapshot if isinstance(snapshot, dict) else {}
    periods = list(snap.get("carbon_periods") or [])
    greener_nights = list(snap.get("greener_nights") or [])
    now = dt_util.now(UK_TZ)
    title = greener_card_title(periods, now=now)
    rewards = snap.get("rewards") if isinstance(snap.get("rewards"), dict) else {}
    return {
        "fetched_at": snap.get("fetched_at"),
        "history_count": history_count,
        "title": title,
        "greener_nights": greener_nights,
        "carbon_periods": periods,
        "timeline": build_greener_timeline(periods, greener_nights, now=now),
        "green_threshold_gco2": GREEN_THRESHOLD_GCO2,
        "postcode": snap.get("postcode"),
        "errors": snap.get("errors") or {},
        "rewards": {
            "loyalty_points": rewards.get("loyalty_points"),
            "loyalty_monetary_amount": rewards.get("loyalty_monetary_amount"),
            "account_balance_pence": rewards.get("account_balance_pence"),
            "current_import_p_per_kwh": current_import_p_per_kwh,
        },
    }
