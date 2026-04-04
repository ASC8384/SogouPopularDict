import builtins

import scripts.download_and_convert as download_and_convert


def test_run_update_returns_no_update_without_downloading(monkeypatch):
    saved_versions = []

    monkeypatch.setattr(
        download_and_convert,
        "get_latest_version_info",
        lambda: {"version": 100, "update_time": "2026-04-04 00:00:00"},
    )
    monkeypatch.setattr(download_and_convert, "load_version_info", lambda: {"version": 100})

    def fail_download():
        raise AssertionError("download should not run when there is no update")

    monkeypatch.setattr(download_and_convert, "download_scel_file", fail_download)
    monkeypatch.setattr(
        download_and_convert,
        "save_version_info",
        lambda version_info: saved_versions.append(version_info),
    )

    status = download_and_convert.run_update()

    assert status == "no_update"
    assert saved_versions == []


def test_parse_scel_file_returns_empty_list_when_no_words_found(monkeypatch):
    class FakeFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def seek(self, offset):
            return None

        def read(self, size=-1):
            return b""

    monkeypatch.setattr(download_and_convert, "get_scel_info", lambda path: {"name": "", "word_count": 0})
    monkeypatch.setattr(download_and_convert, "read_uint32", lambda f: 0)
    monkeypatch.setattr(download_and_convert, "read_uint16", lambda f: 0)
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: FakeFile())

    assert download_and_convert.parse_scel_file("dummy.scel") == []


def test_run_update_returns_error_and_does_not_persist_when_parse_produces_no_words(monkeypatch):
    calls = []

    monkeypatch.setattr(
        download_and_convert,
        "get_latest_version_info",
        lambda: {"version": 101, "update_time": "2026-04-04 00:00:00"},
    )
    monkeypatch.setattr(download_and_convert, "load_version_info", lambda: {"version": 100})
    monkeypatch.setattr(download_and_convert, "download_scel_file", lambda: "dummy.scel")
    monkeypatch.setattr(download_and_convert, "parse_scel_file", lambda path: [])
    monkeypatch.setattr(download_and_convert, "save_to_txt", lambda words, path: calls.append(("txt", path)))
    monkeypatch.setattr(download_and_convert, "update_accumulated_words", lambda words: calls.append(("acc", words)))
    monkeypatch.setattr(download_and_convert, "save_version_info", lambda version_info: calls.append(("version", version_info)))

    assert download_and_convert.run_update() == "error"
    assert calls == []
