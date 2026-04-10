import builtins
import io

import scripts.download_and_convert as download_and_convert

def test_run_update_saves_actual_word_count(monkeypatch):
    calls = []

    monkeypatch.setattr(
        download_and_convert,
        "get_latest_version_info",
        lambda: {"version": 101, "update_time": "2026-04-05 00:00:00", "word_count": 0},
    )
    monkeypatch.setattr(download_and_convert, "load_version_info", lambda: {"version": 100})
    monkeypatch.setattr(download_and_convert, "download_scel_file", lambda: "dummy.scel")
    
    # 模拟解析出3个词
    monkeypatch.setattr(download_and_convert, "parse_scel_file", lambda path: ["词一", "词二", "词三"])
    
    monkeypatch.setattr(download_and_convert, "save_to_txt", lambda words, path: True)
    monkeypatch.setattr(download_and_convert, "update_accumulated_words", lambda words: True)
    
    # 捕获保存的版本信息
    saved_info = []
    monkeypatch.setattr(download_and_convert, "save_version_info", lambda info: saved_info.append(info))

    status = download_and_convert.run_update()

    assert status == "updated"
    assert len(saved_info) == 1
    # 期望 word_count 被更新为实际词条数 3
    assert saved_info[0].get("word_count") == 3

