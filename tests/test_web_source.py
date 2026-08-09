import pytest

from backend.app import sources


@pytest.mark.asyncio
async def test_web_source_maps_searxng(monkeypatch):
    monkeypatch.setenv("TAR_SEARXNG_URL", "https://search.example")

    async def fake_json(url, params, headers=None):
        assert url == "https://search.example/search"
        assert params["q"] == "current event"
        return {
            "results": [
                {
                    "title": "Current Result",
                    "url": "https://example.org/news",
                    "content": "Fresh evidence",
                    "publishedDate": "2026-08-08",
                    "engine": "example",
                }
            ]
        }

    monkeypatch.setattr(sources, "_json", fake_json)
    results = await sources.web("current event", 5)
    assert len(results) == 1
    assert results[0]["source"] == "web"
    assert results[0]["date"] == "2026-08-08"
    assert results[0]["provenance"]["api"] == "SearXNG"


@pytest.mark.asyncio
async def test_web_source_disabled_without_endpoint(monkeypatch):
    monkeypatch.delenv("TAR_SEARXNG_URL", raising=False)
    assert await sources.web("anything", 5) == []
