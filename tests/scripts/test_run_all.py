import os

import scripts.run_all as run_all


def test_main_skips_rime_conversion_when_download_reports_no_update(monkeypatch):
    calls = []

    def fake_run_script(script_path, args=None):
        calls.append(os.path.basename(script_path))
        if script_path.endswith("download_and_convert.py"):
            return "no_update"
        return True

    monkeypatch.setattr(run_all, "run_script", fake_run_script)

    assert run_all.main() is True
    assert calls == ["download_and_convert.py"]
