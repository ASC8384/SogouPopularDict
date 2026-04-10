import builtins
import io
import pathlib

import scripts.download_and_convert as download_and_convert


class EmptyBinaryFile:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def seek(self, offset):
        return None

    def read(self, size=-1):
        return b""


def test_run_update_returns_no_update_without_downloading(monkeypatch):
    saved_versions = []

    monkeypatch.setattr(
        download_and_convert,
        "get_latest_version_info",
        lambda: {"version": 100, "update_time": "2026-04-05 00:00:00"},
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


def test_get_latest_version_info_returns_none_when_version_missing(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = "<html><title>网络流行新词词库</title></html>"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(download_and_convert.requests, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: io.StringIO())

    assert download_and_convert.get_latest_version_info() is None


def test_get_latest_version_info_prefers_page_version_over_download_count(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = """
        <html>
          <head><title>网络流行新词_搜狗输入法词库</title></head>
          <body>
            <span class="num_mark">1415088</span>
            <ul>
              <li><div>更&nbsp;&nbsp;&nbsp;新：2026-04-09 20:50:03</div></li>
              <li><div>版&nbsp;&nbsp;&nbsp;本：第6400个版本</div></li>
            </ul>
            词条: 123 个
          </body>
        </html>
        """

        def raise_for_status(self):
            return None

    monkeypatch.setattr(download_and_convert.requests, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: io.StringIO())

    version_info = download_and_convert.get_latest_version_info()

    assert version_info == {
        "version": 6400,
        "download_count": 1415088,
        "name": "网络流行新词_搜狗输入法",
        "update_time": "2026-04-09 20:50:03",
        "word_count": 123,
    }


def test_get_latest_version_info_returns_none_when_page_version_missing_but_download_count_exists(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = """
        <html>
          <head><title>网络流行新词_搜狗输入法词库</title></head>
          <body>
            <span class="num_mark">1415088</span>
            <ul>
              <li><div>更&nbsp;&nbsp;&nbsp;新：2026-04-09 20:50:03</div></li>
            </ul>
            词条: 123 个
          </body>
        </html>
        """

        def raise_for_status(self):
            return None

    monkeypatch.setattr(download_and_convert.requests, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: io.StringIO())

    assert download_and_convert.get_latest_version_info() is None


def test_normalize_version_info_preserves_explicit_version():
    normalized = download_and_convert.normalize_version_info(
        {"version": 6400, "download_count": 1415088}
    )

    assert normalized["version"] == 6400
    assert normalized["download_count"] == 1415088


def test_should_skip_update_returns_false_for_legacy_download_count_version():
    latest_version_info = {"version": 6400, "download_count": 1415088}
    local_version_info = {"version": 1415049, "download_count": 1415049}

    assert download_and_convert.should_skip_update(latest_version_info, local_version_info) is False


def test_run_update_returns_error_when_latest_version_info_missing(monkeypatch):
    monkeypatch.setattr(download_and_convert, "get_latest_version_info", lambda: None)
    monkeypatch.setattr(download_and_convert, "load_version_info", lambda: {"version": 100})

    def fail_download():
        raise AssertionError("download should not run when latest version info is missing")

    monkeypatch.setattr(download_and_convert, "download_scel_file", fail_download)

    assert download_and_convert.run_update() == "error"


def test_run_update_force_continues_when_latest_version_info_missing(monkeypatch):
    calls = []
    saved_versions = []

    monkeypatch.setattr(download_and_convert, "get_latest_version_info", lambda: None)
    monkeypatch.setattr(
        download_and_convert,
        "load_version_info",
        lambda: {"version": 100, "download_count": 100, "name": "网络流行新词", "word_count": 10},
    )
    monkeypatch.setattr(download_and_convert, "download_scel_file", lambda: calls.append("download") or "dummy.scel")
    monkeypatch.setattr(download_and_convert, "parse_scel_file", lambda path: ["词一", "词二"])
    monkeypatch.setattr(download_and_convert, "save_to_txt", lambda words, path: calls.append(("txt", path, tuple(words))) or True)
    monkeypatch.setattr(download_and_convert, "update_accumulated_words", lambda words: calls.append(("acc", tuple(words))) or True)
    monkeypatch.setattr(download_and_convert, "save_version_info", lambda version_info: saved_versions.append(version_info.copy()))

    status = download_and_convert.run_update(force_update=True)

    assert status == "updated"
    assert calls[0] == "download"
    assert saved_versions[0]["word_count"] == 2
    assert saved_versions[0]["name"] == "网络流行新词"
    assert saved_versions[0]["version"] == 100
    assert saved_versions[0]["download_count"] == 100
    assert saved_versions[0]["update_time"]
    assert len(saved_versions) == 1


def test_parse_scel_file_returns_empty_list_when_no_words_found(monkeypatch):
    monkeypatch.setattr(download_and_convert, "get_scel_info", lambda path: {"name": "", "word_count": 0})
    monkeypatch.setattr(download_and_convert, "read_uint32", lambda f: 0)
    monkeypatch.setattr(download_and_convert, "read_uint16", lambda f: 0)
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: EmptyBinaryFile())

    assert download_and_convert.parse_scel_file("dummy.scel") == []


def test_run_update_returns_error_and_does_not_persist_when_parse_produces_no_words(monkeypatch):
    calls = []

    monkeypatch.setattr(
        download_and_convert,
        "get_latest_version_info",
        lambda: {"version": 101, "update_time": "2026-04-05 00:00:00"},
    )
    monkeypatch.setattr(download_and_convert, "load_version_info", lambda: {"version": 100})
    monkeypatch.setattr(download_and_convert, "download_scel_file", lambda: "dummy.scel")
    monkeypatch.setattr(download_and_convert, "parse_scel_file", lambda path: [])
    monkeypatch.setattr(download_and_convert, "save_to_txt", lambda words, path: calls.append(("txt", path)))
    monkeypatch.setattr(download_and_convert, "update_accumulated_words", lambda words: calls.append(("acc", words)))
    monkeypatch.setattr(download_and_convert, "save_version_info", lambda version_info: calls.append(("version", version_info)))

    assert download_and_convert.run_update() == "error"
    assert calls == []


def test_load_version_info_is_defined_once():
    source = pathlib.Path(download_and_convert.__file__).read_text(encoding="utf-8")

    assert source.count("def load_version_info(") == 1
