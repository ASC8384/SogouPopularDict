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
