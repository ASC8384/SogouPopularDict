import builtins
import io
import pathlib

import scripts.download_and_convert as download_and_convert


class FakeBinaryFile:
    def __init__(self, values):
        self.values = list(values)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def seek(self, offset):
        return None

    def read(self, size=-1):
        return b"\x00" * max(size, 0)


class CaptureWriteFile:
    def __init__(self):
        self.buffer = io.StringIO()

    def __enter__(self):
        return self.buffer

    def __exit__(self, exc_type, exc, tb):
        return False


class ReadTextFile:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return io.StringIO(self.text)

    def __exit__(self, exc_type, exc, tb):
        return False


class CaptureBinaryFile:
    def __init__(self):
        self.content = b""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def write(self, content):
        self.content += content
        return len(content)


class FakeSCELFile:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def seek(self, offset):
        return None

    def read(self, size=-1):
        if size == 4:
            return b"@\x15\x00\x00"
        return b"\x00" * max(size, 0)


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


def test_parse_scel_file_returns_word_entries_with_pronunciations(monkeypatch):
    uint16_values = iter([
        10,  # pinyin_idx 1
        4,   # pinyin_len 1
        20,  # pinyin_idx 2
        10,  # pinyin_len 2
        1,   # same_pinyin_count
        4,   # pinyin_index_len
        10,  # index -> da
        20,  # index -> huang
        4,   # word_len
        10,  # skip type
        0,   # break same_pinyin_count
        0,   # break pinyin_index_len
    ])
    uint32_values = iter([
        2,   # pinyin_count
        1,   # skip frequency
    ])

    class SequencedSCELFile:
        def __init__(self):
            self.read_calls = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def seek(self, offset):
            return None

        def read(self, size=-1):
            payloads = [
                "da".encode("utf-16le"),
                "huang".encode("utf-16le"),
                "大黄".encode("utf-16le"),
                b"\x00" * 6,
            ]
            payload = payloads[self.read_calls]
            self.read_calls += 1
            return payload

    monkeypatch.setattr(download_and_convert, "get_scel_info", lambda path: {"name": "测试词库", "word_count": 1})
    monkeypatch.setattr(download_and_convert, "read_uint32", lambda f: next(uint32_values))
    monkeypatch.setattr(download_and_convert, "read_uint16", lambda f: next(uint16_values))
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: SequencedSCELFile())

    assert download_and_convert.parse_scel_file("dummy.scel") == [
        {"word": "大黄", "pinyin": "da huang", "source": "scel"}
    ]



def test_update_accumulated_data_keeps_existing_pronunciation_for_old_words(tmp_path):
    accumulated_txt = tmp_path / "accumulated.txt"
    accumulated_txt.write_text("旧词\n", encoding="utf-8")
    accumulated_tsv = tmp_path / "accumulated.tsv"
    accumulated_tsv.write_text("旧词\tjiu ci\n", encoding="utf-8")

    entries = [
        {"word": "旧词", "pinyin": "xin yin", "source": "scel"},
        {"word": "新词", "pinyin": "xin ci", "source": "scel"},
    ]

    old_txt = download_and_convert.ACCUMULATED_TXT_PATH
    old_tsv = download_and_convert.ACCUMULATED_PINYIN_PATH
    download_and_convert.ACCUMULATED_TXT_PATH = str(accumulated_txt)
    download_and_convert.ACCUMULATED_PINYIN_PATH = str(accumulated_tsv)
    try:
        assert download_and_convert.update_accumulated_data(entries) is True
    finally:
        download_and_convert.ACCUMULATED_TXT_PATH = old_txt
        download_and_convert.ACCUMULATED_PINYIN_PATH = old_tsv

    assert accumulated_txt.read_text(encoding="utf-8") == "新词\n旧词\n"
    assert accumulated_tsv.read_text(encoding="utf-8") == "新词\txin ci\n旧词\tjiu ci\n"


def test_save_to_txt_accepts_word_entries(tmp_path):
    output_path = tmp_path / "words.txt"

    assert download_and_convert.save_to_txt(
        [{"word": "词一", "pinyin": "ci yi"}, {"word": "词二", "pinyin": "ci er"}],
        str(output_path),
    ) is True

    assert output_path.read_text(encoding="utf-8") == "词一\n词二\n"


def test_save_pronunciations_to_tsv_writes_word_and_pinyin(tmp_path):
    output_path = tmp_path / "words.tsv"

    assert download_and_convert.save_pronunciations_to_tsv(
        {"词一": "ci yi", "词二": "ci er"},
        str(output_path),
    ) is True

    assert output_path.read_text(encoding="utf-8") == "词一\tci yi\n词二\tci er\n"


def test_load_pronunciations_from_tsv_reads_mapping(tmp_path):
    input_path = tmp_path / "words.tsv"
    input_path.write_text("词一\tci yi\n词二\tci er\n", encoding="utf-8")

    assert download_and_convert.load_pronunciations_from_tsv(str(input_path)) == {
        "词一": "ci yi",
        "词二": "ci er",
    }


def test_run_update_persists_current_and_accumulated_pronunciations(monkeypatch):
    calls = []
    saved_versions = []
    entries = [{"word": "词一", "pinyin": "ci yi", "source": "scel"}]

    monkeypatch.setattr(
        download_and_convert,
        "get_latest_version_info",
        lambda: {"version": 101, "update_time": "2026-04-05 00:00:00"},
    )
    monkeypatch.setattr(download_and_convert, "load_version_info", lambda: {"version": 100})
    monkeypatch.setattr(download_and_convert, "download_scel_file", lambda: "dummy.scel")
    monkeypatch.setattr(download_and_convert, "parse_scel_file", lambda path: entries)
    monkeypatch.setattr(download_and_convert, "save_to_txt", lambda words, path: calls.append(("txt", path, tuple(words))) or True)
    monkeypatch.setattr(download_and_convert, "save_pronunciations_to_tsv", lambda mapping, path: calls.append(("tsv", path, dict(mapping))) or True)
    monkeypatch.setattr(download_and_convert, "update_accumulated_data", lambda items: calls.append(("acc", tuple(items))) or True)
    monkeypatch.setattr(download_and_convert, "save_version_info", lambda info: saved_versions.append(info))

    assert download_and_convert.run_update() == "updated"
    assert ("txt", download_and_convert.CURRENT_TXT_PATH, tuple(entries)) in calls
    assert ("tsv", download_and_convert.CURRENT_PINYIN_PATH, {"词一": "ci yi"}) in calls
    assert ("acc", tuple(entries)) in calls
    assert saved_versions[0]["word_count"] == 1


def test_build_pronunciation_map_prefers_first_occurrence():
    entries = [
        {"word": "旧词", "pinyin": "jiu ci", "source": "scel"},
        {"word": "旧词", "pinyin": "xin ci", "source": "scel"},
    ]

    assert download_and_convert.build_pronunciation_map(entries) == {"旧词": "jiu ci"}


def test_extract_words_returns_words_in_order():
    entries = [
        {"word": "词一", "pinyin": "ci yi", "source": "scel"},
        {"word": "词二", "pinyin": "ci er", "source": "scel"},
    ]

    assert download_and_convert.extract_words(entries) == ["词一", "词二"]


def test_load_accumulated_pronunciations_returns_empty_dict_when_missing(tmp_path):
    missing_path = tmp_path / "missing.tsv"

    old_tsv = download_and_convert.ACCUMULATED_PINYIN_PATH
    download_and_convert.ACCUMULATED_PINYIN_PATH = str(missing_path)
    try:
        assert download_and_convert.load_accumulated_pronunciations() == {}
    finally:
        download_and_convert.ACCUMULATED_PINYIN_PATH = old_tsv


def test_load_current_pronunciations_returns_empty_dict_when_missing(tmp_path):
    missing_path = tmp_path / "missing.tsv"

    old_tsv = download_and_convert.CURRENT_PINYIN_PATH
    download_and_convert.CURRENT_PINYIN_PATH = str(missing_path)
    try:
        assert download_and_convert.load_current_pronunciations() == {}
    finally:
        download_and_convert.CURRENT_PINYIN_PATH = old_tsv


def test_save_pronunciations_to_tsv_returns_false_on_error(monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boom")))

    assert download_and_convert.save_pronunciations_to_tsv({"词一": "ci yi"}, "dummy.tsv") is False


def test_load_pronunciations_from_tsv_skips_blank_lines(tmp_path):
    input_path = tmp_path / "words.tsv"
    input_path.write_text("词一\tci yi\n\n词二\tci er\n", encoding="utf-8")

    assert download_and_convert.load_pronunciations_from_tsv(str(input_path)) == {
        "词一": "ci yi",
        "词二": "ci er",
    }


def test_load_pronunciations_from_tsv_returns_empty_dict_on_bad_line(tmp_path):
    input_path = tmp_path / "words.tsv"
    input_path.write_text("坏行\n", encoding="utf-8")

    assert download_and_convert.load_pronunciations_from_tsv(str(input_path)) == {}


def test_update_accumulated_data_returns_false_when_txt_save_fails(monkeypatch):
    monkeypatch.setattr(download_and_convert, "load_accumulated_words", lambda: set())
    monkeypatch.setattr(download_and_convert, "load_accumulated_pronunciations", lambda: {})
    monkeypatch.setattr(download_and_convert, "save_words_to_txt", lambda words, path: False)

    assert download_and_convert.update_accumulated_data([
        {"word": "词一", "pinyin": "ci yi", "source": "scel"}
    ]) is False


def test_update_accumulated_data_returns_false_when_tsv_save_fails(monkeypatch):
    monkeypatch.setattr(download_and_convert, "load_accumulated_words", lambda: set())
    monkeypatch.setattr(download_and_convert, "load_accumulated_pronunciations", lambda: {})
    monkeypatch.setattr(download_and_convert, "save_words_to_txt", lambda words, path: True)
    monkeypatch.setattr(download_and_convert, "save_pronunciations_to_tsv", lambda mapping, path: False)

    assert download_and_convert.update_accumulated_data([
        {"word": "词一", "pinyin": "ci yi", "source": "scel"}
    ]) is False


def test_save_words_to_txt_writes_sorted_words(tmp_path):
    output_path = tmp_path / "words.txt"

    assert download_and_convert.save_words_to_txt({"词二", "词一"}, str(output_path)) is True
    assert output_path.read_text(encoding="utf-8") == "词一\n词二\n"


def test_save_words_to_txt_returns_false_on_error(monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boom")))

    assert download_and_convert.save_words_to_txt({"词一"}, "dummy.txt") is False


def test_build_pronunciation_map_skips_entries_without_pinyin():
    entries = [
        {"word": "词一", "pinyin": "", "source": "scel"},
        {"word": "词二", "pinyin": "ci er", "source": "scel"},
    ]

    assert download_and_convert.build_pronunciation_map(entries) == {"词二": "ci er"}


def test_extract_words_skips_entries_without_word():
    entries = [
        {"word": "", "pinyin": "ci yi", "source": "scel"},
        {"word": "词二", "pinyin": "ci er", "source": "scel"},
    ]

    assert download_and_convert.extract_words(entries) == ["词二"]


def test_run_update_returns_error_when_current_tsv_save_fails(monkeypatch):
    entries = [{"word": "词一", "pinyin": "ci yi", "source": "scel"}]

    monkeypatch.setattr(
        download_and_convert,
        "get_latest_version_info",
        lambda: {"version": 101, "update_time": "2026-04-05 00:00:00"},
    )
    monkeypatch.setattr(download_and_convert, "load_version_info", lambda: {"version": 100})
    monkeypatch.setattr(download_and_convert, "download_scel_file", lambda: "dummy.scel")
    monkeypatch.setattr(download_and_convert, "parse_scel_file", lambda path: entries)
    monkeypatch.setattr(download_and_convert, "save_to_txt", lambda words, path: True)
    monkeypatch.setattr(download_and_convert, "save_pronunciations_to_tsv", lambda mapping, path: False)

    assert download_and_convert.run_update() == "error"


def test_run_update_returns_error_when_accumulated_update_fails(monkeypatch):
    entries = [{"word": "词一", "pinyin": "ci yi", "source": "scel"}]

    monkeypatch.setattr(
        download_and_convert,
        "get_latest_version_info",
        lambda: {"version": 101, "update_time": "2026-04-05 00:00:00"},
    )
    monkeypatch.setattr(download_and_convert, "load_version_info", lambda: {"version": 100})
    monkeypatch.setattr(download_and_convert, "download_scel_file", lambda: "dummy.scel")
    monkeypatch.setattr(download_and_convert, "parse_scel_file", lambda path: entries)
    monkeypatch.setattr(download_and_convert, "save_to_txt", lambda words, path: True)
    monkeypatch.setattr(download_and_convert, "save_pronunciations_to_tsv", lambda mapping, path: True)
    monkeypatch.setattr(download_and_convert, "update_accumulated_data", lambda items: False)

    assert download_and_convert.run_update() == "error"


def test_run_update_force_continues_when_latest_version_info_missing(monkeypatch):
    calls = []
    saved_versions = []
    entries = [
        {"word": "词一", "pinyin": "ci yi", "source": "scel"},
        {"word": "词二", "pinyin": "ci er", "source": "scel"},
    ]

    monkeypatch.setattr(download_and_convert, "get_latest_version_info", lambda: None)
    monkeypatch.setattr(
        download_and_convert,
        "load_version_info",
        lambda: {"version": 100, "download_count": 100, "name": "网络流行新词", "word_count": 10},
    )
    monkeypatch.setattr(download_and_convert, "download_scel_file", lambda: calls.append("download") or "dummy.scel")
    monkeypatch.setattr(download_and_convert, "parse_scel_file", lambda path: entries)
    monkeypatch.setattr(download_and_convert, "save_to_txt", lambda words, path: calls.append(("txt", path, tuple(words))) or True)
    monkeypatch.setattr(download_and_convert, "save_pronunciations_to_tsv", lambda mapping, path: calls.append(("tsv", path, dict(mapping))) or True)
    monkeypatch.setattr(download_and_convert, "update_accumulated_data", lambda words: calls.append(("acc", tuple(words))) or True)
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
    monkeypatch.setattr(download_and_convert, "save_pronunciations_to_tsv", lambda mapping, path: calls.append(("tsv", path)))
    monkeypatch.setattr(download_and_convert, "update_accumulated_data", lambda words: calls.append(("acc", words)))
    monkeypatch.setattr(download_and_convert, "save_version_info", lambda version_info: calls.append(("version", version_info)))

    assert download_and_convert.run_update() == "error"
    assert calls == []


def test_load_version_info_is_defined_once():
    source = pathlib.Path(download_and_convert.__file__).read_text(encoding="utf-8")

    assert source.count("def load_version_info(") == 1
