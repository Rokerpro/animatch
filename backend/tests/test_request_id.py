import logging

import pytest
from httpx import AsyncClient

from app.core.request_id import RequestIdFilter, request_id_var


@pytest.mark.asyncio
async def test_generates_request_id_when_missing(client: AsyncClient):
    response = await client.get("/api/health")
    assert len(response.headers["x-request-id"]) == 32


@pytest.mark.asyncio
async def test_reuses_valid_incoming_request_id(client: AsyncClient):
    response = await client.get(
        "/api/health", headers={"X-Request-ID": "trace-12345678"}
    )
    assert response.headers["x-request-id"] == "trace-12345678"


@pytest.mark.asyncio
async def test_replaces_malformed_request_id(client: AsyncClient):
    response = await client.get("/api/health", headers={"X-Request-ID": "bad id!"})
    assert response.headers["x-request-id"] != "bad id!"
    assert len(response.headers["x-request-id"]) == 32


def test_log_filter_adds_request_id():
    token = request_id_var.set("abc12345")
    try:
        record = logging.LogRecord("x", logging.INFO, "f", 1, "m", None, None)
        assert RequestIdFilter().filter(record)
        assert record.request_id == "abc12345"  # type: ignore[attr-defined]
    finally:
        request_id_var.reset(token)
