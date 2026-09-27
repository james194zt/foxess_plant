"""E.ON Next tariff client (Kraken GraphQL + public products REST).

E.ON Next publishes no API keys: the only way in is the customer's email/password
exchanged for a Kraken JWT (``obtainKrakenToken``), the same flow the E.ON Next app and
the community ``eon_next`` integration use. The result is shaped as an
``OctopusTariffSnapshot`` so SmartCharge, tariff sensors and schedule apply work unchanged.

Rates: public ``/v1/products/.../standard-unit-rates/`` first (same shape as Octopus);
when E.ON's REST API cannot serve the tariff (time-of-use ``E-TOU-*``, day/night, retired
or private export products → 400/404/410) fall back to GraphQL ``applicableRates``.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .eon_next_parse import (
    classify_eon_tariff_code,
    graphql_error_code,
    graphql_error_message,
    graphql_nodes_to_rows,
    meters_from_accounts,
    normalize_rest_rows,
    pick_meter,
)
from .octopus_api import OctopusApiError
from .octopus_tariff import (
    OctopusMeterSummary,
    OctopusTariffSnapshot,
    build_schedule_from_rates,
    rate_at,
    standing_charge_at,
)

_LOGGER = logging.getLogger(__name__)

EON_NEXT_BASE_URL = "https://api.eonnext-kraken.energy/v1"
EON_NEXT_GRAPHQL_URL = f"{EON_NEXT_BASE_URL}/graphql/"

# Kraken token expired / invalid → mint a fresh one and retry once.
_AUTH_RETRY_CODES = ("KT-CT-1139", "KT-CT-1111", "KT-CT-1143", "KT-CT-1112")
# REST statuses meaning "products API cannot serve this tariff" (not an outage).
_REST_UNAVAILABLE = (400, 404, 410)
_RATES_PAGE_SIZE = 100
_RATES_MAX_PAGES = 10
_REST_MAX_PAGES = 5

_TOKEN_MUTATION = """mutation obtainKrakenToken($input: ObtainJSONWebTokenInput!) {
  obtainKrakenToken(input: $input) { token refreshToken payload }
}"""

_VIEWER_QUERY = "{ viewer { accounts { number } } }"

_ACCOUNT_QUERY = """{
  account(accountNumber: %s) {
    number
    properties {
      electricityMeterPoints {
        mpan
        direction
        agreements {
          validFrom
          validTo
          tariff { ... on TariffType { tariffCode displayName productCode } }
        }
      }
    }
  }
}"""

_APPLICABLE_RATES_QUERY = """{
  applicableRates(accountNumber: %s, mpxn: %s, startAt: %s, endAt: %s, first: %d, after: %s) {
    edges { node { value validFrom validTo } }
    pageInfo { hasNextPage endCursor }
  }
}"""

_APPLICABLE_STANDING_QUERY = """{
  applicableStandingCharges(accountNumber: %s, mpxn: %s, startAt: %s, endAt: %s, first: 50) {
    edges { node { value validFrom validTo } }
  }
}"""


class EonNextApiError(OctopusApiError):
    """E.ON Next request failed (subclass so shared tariff error handling catches it)."""


def _q(value: str) -> str:
    """Quote a string as a GraphQL literal."""
    return json.dumps(str(value))


def _iso(dt: datetime) -> str:
    return dt_util.as_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


class EonNextApiClient:
    """Email/password Kraken client for E.ON Next. Keep one per login to reuse tokens."""

    def __init__(self, hass: HomeAssistant, *, email: str, password: str) -> None:
        self._email = (email or "").strip()
        self._password = password or ""
        self._session = async_get_clientsession(hass)
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._token_exp: float = 0.0

    def matches(self, email: str, password: str) -> bool:
        return self._email == (email or "").strip() and self._password == (password or "")

    async def _post(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        try:
            async with self._session.post(
                EON_NEXT_GRAPHQL_URL,
                json=payload,
                headers={
                    "User-Agent": "FoxESS-Plant/1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    **headers,
                },
                timeout=aiohttp.ClientTimeout(total=45),
            ) as resp:
                text = await resp.text()
                if resp.status == 429 or (resp.status == 403 and not text.lstrip().startswith("{")):
                    # A non-JSON 403 comes from the CDN/WAF: rate limiting, not a bad login.
                    raise EonNextApiError(f"E.ON Next rate limit (HTTP {resp.status}) — try again later")
                if resp.status >= 400:
                    raise EonNextApiError(f"E.ON Next GraphQL HTTP {resp.status}: {text[:160]}")
                try:
                    body = json.loads(text) if text else {}
                except json.JSONDecodeError as err:
                    raise EonNextApiError("Unexpected E.ON Next response") from err
        except aiohttp.ClientError as err:
            raise EonNextApiError(f"E.ON Next network error: {err}") from err
        if not isinstance(body, dict):
            raise EonNextApiError("Unexpected E.ON Next response")
        return body

    async def _mint(self, token_input: dict[str, str]) -> bool:
        body = await self._post({"query": _TOKEN_MUTATION, "variables": {"input": token_input}}, {})
        if body.get("errors"):
            if "refreshToken" in token_input:
                return False
            raise EonNextApiError(f"E.ON Next login failed: {graphql_error_message(body['errors'])}")
        block = (body.get("data") or {}).get("obtainKrakenToken") or {}
        token = block.get("token")
        if not token:
            if "refreshToken" in token_input:
                return False
            raise EonNextApiError("E.ON Next login failed: no token returned")
        payload = block.get("payload") or {}
        # E.ON returns payload as a GenericScalar: a dict or a JSON string.
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        exp = payload.get("exp") if isinstance(payload, dict) else None
        self._token = str(token)
        self._refresh_token = block.get("refreshToken") or None
        self._token_exp = float(exp) if exp else time.time() + 30 * 60
        return True

    async def _ensure_token(self, *, force: bool = False) -> str:
        if not force and self._token and self._token_exp - 300 > time.time():
            return self._token
        if not self._email or not self._password:
            raise EonNextApiError("E.ON Next email and password are required")
        if self._refresh_token and not force and await self._mint({"refreshToken": self._refresh_token}):
            return str(self._token)
        await self._mint({"email": self._email, "password": self._password})
        return str(self._token)

    async def graphql(self, query: str, *, _retried: bool = False) -> dict[str, Any]:
        token = await self._ensure_token(force=_retried)
        body = await self._post({"query": query}, {"Authorization": f"JWT {token}"})
        errors = body.get("errors")
        if errors:
            if not _retried and graphql_error_code(errors) in _AUTH_RETRY_CODES:
                self._token = None
                return await self.graphql(query, _retried=True)
            raise EonNextApiError(f"E.ON Next: {graphql_error_message(errors)}")
        data = body.get("data")
        if not isinstance(data, dict):
            raise EonNextApiError("E.ON Next returned no data")
        return data

    async def list_account_numbers(self) -> list[str]:
        data = await self.graphql(_VIEWER_QUERY)
        accounts = (data.get("viewer") or {}).get("accounts") or []
        return [
            str(a["number"]).strip().upper()
            for a in accounts
            if isinstance(a, dict) and a.get("number")
        ]

    async def get_account(self, account_number: str) -> dict[str, Any]:
        data = await self.graphql(_ACCOUNT_QUERY % _q(account_number.strip().upper()))
        account = data.get("account")
        if not isinstance(account, dict):
            raise EonNextApiError(f"E.ON Next account {account_number} not found")
        return account

    async def _rest_rows(self, path: str, params: dict[str, str]) -> tuple[list[dict[str, Any]], int | None]:
        """GET a paginated public products endpoint. Returns (rows, status_if_unavailable)."""
        url: str | None = f"{EON_NEXT_BASE_URL}{path}?{urlencode(params)}"
        rows: list[dict[str, Any]] = []
        pages = 0
        while url and pages < _REST_MAX_PAGES:
            try:
                async with self._session.get(
                    url,
                    headers={"User-Agent": "FoxESS-Plant/1.0", "Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=45),
                ) as resp:
                    text = await resp.text()
                    if resp.status in _REST_UNAVAILABLE:
                        return rows, resp.status
                    if resp.status == 429:
                        raise EonNextApiError("E.ON Next rate limit (HTTP 429) — try again later")
                    if resp.status != 200:
                        raise EonNextApiError(f"E.ON Next REST HTTP {resp.status}: {text[:160]}")
                    payload = json.loads(text) if text else {}
            except aiohttp.ClientError as err:
                raise EonNextApiError(f"E.ON Next network error: {err}") from err
            except json.JSONDecodeError as err:
                raise EonNextApiError("Unexpected E.ON Next REST response") from err
            batch = payload.get("results") if isinstance(payload, dict) else None
            if isinstance(batch, list):
                rows.extend(r for r in batch if isinstance(r, dict))
            url = payload.get("next") if isinstance(payload, dict) else None
            pages += 1
        return rows, None

    async def _applicable_rates(
        self, account_number: str, mpan: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        after = "null"
        for _ in range(_RATES_MAX_PAGES):
            data = await self.graphql(
                _APPLICABLE_RATES_QUERY
                % (_q(account_number), _q(mpan), _q(_iso(start)), _q(_iso(end)), _RATES_PAGE_SIZE, after)
            )
            connection = data.get("applicableRates") or {}
            nodes.extend(connection.get("edges") or [])
            page = connection.get("pageInfo") or {}
            if not page.get("hasNextPage") or not page.get("endCursor"):
                break
            after = _q(page["endCursor"])
        return graphql_nodes_to_rows({"edges": nodes})

    async def get_unit_rates(
        self, meter: dict[str, Any], start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        product, tariff = meter.get("product_code"), meter.get("tariff_code")
        if product and tariff:
            rows, unavailable = await self._rest_rows(
                f"/products/{product}/electricity-tariffs/{tariff}/standard-unit-rates/",
                {"period_from": _iso(start), "period_to": _iso(end)},
            )
            if unavailable is None and rows:
                return normalize_rest_rows(rows)
            _LOGGER.debug(
                "E.ON Next REST rates unavailable for %s (HTTP %s) — using applicableRates",
                tariff,
                unavailable,
            )
        return await self._applicable_rates(meter["account_number"], meter["mpan"], start, end)

    async def get_standing_charges(
        self, meter: dict[str, Any], start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        product, tariff = meter.get("product_code"), meter.get("tariff_code")
        if product and tariff:
            rows, unavailable = await self._rest_rows(
                f"/products/{product}/electricity-tariffs/{tariff}/standing-charges/",
                {"period_from": _iso(start), "period_to": _iso(end)},
            )
            if unavailable is None and rows:
                return normalize_rest_rows(rows)
        data = await self.graphql(
            _APPLICABLE_STANDING_QUERY
            % (_q(meter["account_number"]), _q(meter["mpan"]), _q(_iso(start)), _q(_iso(end)))
        )
        return graphql_nodes_to_rows(data.get("applicableStandingCharges"))


async def discover_eon_next_meters(
    client: EonNextApiClient,
    *,
    account_number: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Load every account on the login — E.ON can put the export MPAN on its own account."""
    numbers = await client.list_account_numbers()
    configured = (account_number or "").strip().upper()
    if configured and configured not in numbers:
        numbers.insert(0, configured)
    if not numbers:
        raise EonNextApiError("No accounts found on this E.ON Next login")
    accounts = [await client.get_account(n) for n in numbers]
    imports, exports = meters_from_accounts(accounts, now=dt_util.utcnow())
    return imports, exports, numbers


def _summary(meter: dict[str, Any] | None) -> OctopusMeterSummary | None:
    if meter is None:
        return None
    return OctopusMeterSummary(
        mpan=meter["mpan"],
        serial=None,
        is_export=bool(meter["is_export"]),
        tariff_code=meter.get("tariff_code"),
        product_code=meter.get("product_code"),
        display_name=meter.get("display_name") or meter["mpan"],
    )


def meter_list_for_cache(meters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "mpan": m["mpan"],
            "serial": None,
            "tariff_code": m.get("tariff_code"),
            "display_name": m.get("display_name"),
            "account_number": m.get("account_number"),
        }
        for m in meters
    ]


async def fetch_eon_next_tariff_snapshot(
    client: EonNextApiClient,
    *,
    account_number: str | None = None,
    import_mpan: str | None = None,
    export_mpan: str | None = None,
    include_export: bool = True,
) -> tuple[OctopusTariffSnapshot, list[dict[str, Any]], list[dict[str, Any]]]:
    imports, exports, _numbers = await discover_eon_next_meters(client, account_number=account_number)
    if not imports:
        raise EonNextApiError("No import electricity meter found on this E.ON Next login")
    try:
        import_meter = pick_meter(imports, import_mpan, role="import", preferred_account=account_number)
        export_meter = None if not include_export else pick_meter(
            exports,
            export_mpan,
            role="export",
            preferred_account=account_number,
            allow_first=True,
        )
    except ValueError as err:
        raise EonNextApiError(str(err)) from err
    if import_meter is None or not import_meter.get("tariff_code"):
        raise EonNextApiError("E.ON Next import meter has no active tariff agreement")

    now = dt_util.utcnow()
    # Start at local midnight: the schedule builder samples every hour of today.
    local_midnight = dt_util.as_local(now).replace(hour=0, minute=0, second=0, microsecond=0)
    start = dt_util.as_utc(local_midnight) - timedelta(hours=1)
    end = now + timedelta(days=2)

    import_rates = await client.get_unit_rates(import_meter, start, end)
    if not import_rates:
        raise EonNextApiError(f"E.ON Next returned no unit rates for {import_meter['tariff_code']}")

    export_rates: list[dict[str, Any]] = []
    export_warning: str | None = None
    if export_meter is None:
        if include_export:
            _LOGGER.info("E.ON Next: no export meter on this login — export rates unavailable")
    elif not export_meter.get("tariff_code"):
        export_warning = f"Export meter {export_meter['mpan']} has no active tariff agreement"
    else:
        try:
            export_rates = await client.get_unit_rates(export_meter, start, end)
        except EonNextApiError as err:
            export_warning = f"Export unit rates failed: {err}"
            _LOGGER.warning("E.ON Next export rates failed: %s", err)
        if not export_rates and not export_warning:
            export_warning = (
                f"Export tariff {export_meter['tariff_code']} returned no unit rates for the window"
            )

    try:
        standing_rows = await client.get_standing_charges(import_meter, start, end)
    except EonNextApiError as err:
        _LOGGER.warning("E.ON Next standing charge failed: %s", err)
        standing_rows = []

    tariff_type = classify_eon_tariff_code(import_meter["tariff_code"])
    snapshot = OctopusTariffSnapshot(
        tariff_type=tariff_type,
        import_meter=_summary(import_meter),
        export_meter=_summary(export_meter),
        import_rates=import_rates,
        export_rates=export_rates,
        import_standing_p_per_day=standing_charge_at(now, standing_rows),
        current_import_p_per_kwh=rate_at(now, import_rates),
        current_export_p_per_kwh=rate_at(now, export_rates) if export_rates else None,
        # E.ON has no half-hourly variable products, so the daily schedule always applies.
        schedule=build_schedule_from_rates(import_rates, export_rates or None),
        last_fetch_at=now.isoformat(),
        last_error=export_warning,
    )
    return snapshot, imports, exports


async def test_eon_next_connection(
    client: EonNextApiClient,
    *,
    account_number: str | None = None,
) -> dict[str, Any]:
    imports, exports, numbers = await discover_eon_next_meters(client, account_number=account_number)
    return {
        "account_number": (account_number or (numbers[0] if numbers else "")).strip().upper(),
        "account_numbers": numbers,
        "import_meters": meter_list_for_cache(imports),
        "export_meters": meter_list_for_cache(exports),
    }
