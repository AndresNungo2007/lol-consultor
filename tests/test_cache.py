from __future__ import annotations

from lol_consultor.cache import TTLCache


def test_get_or_set_fetches_once_within_ttl(tmp_path):
    cache = TTLCache(tmp_path)
    calls = []

    def fetch():
        calls.append(1)
        return {"value": 42}

    first = cache.get_or_set("key", ttl_seconds=3600, fetch_fn=fetch)
    second = cache.get_or_set("key", ttl_seconds=3600, fetch_fn=fetch)

    assert first == {"value": 42}
    assert second == {"value": 42}
    assert len(calls) == 1  # segunda llamada vino del cache, no de fetch_fn


def test_get_or_set_refetches_after_ttl_expires(tmp_path, monkeypatch):
    cache = TTLCache(tmp_path)
    calls = []

    def fetch():
        calls.append(1)
        return {"n": len(calls)}

    cache.get_or_set("key", ttl_seconds=0, fetch_fn=fetch)
    cache.get_or_set("key", ttl_seconds=0, fetch_fn=fetch)

    assert len(calls) == 2  # ttl_seconds=0 -> siempre expirado


def test_get_or_set_recovers_from_corrupted_cache_file(tmp_path):
    cache = TTLCache(tmp_path)
    path = cache._path("key")
    path.write_text("no es json valido", encoding="utf-8")

    result = cache.get_or_set("key", ttl_seconds=3600, fetch_fn=lambda: {"ok": True})

    assert result == {"ok": True}


def test_get_or_set_force_refetches_fresh_entries(tmp_path):
    cache = TTLCache(tmp_path)
    calls = []

    def fetch():
        calls.append(1)
        return {"n": len(calls)}

    cache.get_or_set("key", ttl_seconds=3600, fetch_fn=fetch)
    result = cache.get_or_set("key", ttl_seconds=3600, fetch_fn=fetch, force=True)

    assert len(calls) == 2  # force ignora el cache vigente
    assert result == {"n": 2}


def test_clear_removes_all_entries(tmp_path):
    cache = TTLCache(tmp_path)
    cache.get_or_set("a", ttl_seconds=3600, fetch_fn=lambda: 1)
    cache.get_or_set("b", ttl_seconds=3600, fetch_fn=lambda: 2)

    removed = cache.clear()

    assert removed == 2
    calls = []
    cache.get_or_set("a", ttl_seconds=3600, fetch_fn=lambda: calls.append(1) or 1)
    assert calls  # tras clear, se vuelve a descargar
