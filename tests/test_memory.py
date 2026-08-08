from backend.app.memory import recall, remember, stats


def test_memory_round_trip():
    remember([
        {
            "source": "test_archive",
            "title": "Freedmen record example",
            "url": "urn:test:freedmen:1",
            "snippet": "A historical Freedmen record from an archival collection.",
            "confidence": 0.95,
        }
    ])
    results = recall("historical Freedmen archive", limit=5)
    assert any(item["url"] == "urn:test:freedmen:1" for item in results)
    assert stats()["records"] >= 1


def test_memory_deduplicates_source_records():
    item = {
        "source": "test_archive",
        "title": "Dawes record example",
        "url": "urn:test:dawes:1",
        "snippet": "Dawes enrollment record.",
    }
    remember([item])
    before = stats()["records"]
    remember([item])
    assert stats()["records"] == before
