import scripts.repair_pronunciation_data as repair_pronunciation_data


def test_load_yaml_pronunciations_reads_entries(tmp_path):
    yaml_path = tmp_path / "dict.yaml"
    yaml_path.write_text(
        "# header\n---\nname: test\nversion: \"2026.04.14\"\nsort: by_weight\nuse_preset_vocabulary: true\n...\n\n词一\tci yi\n词二\tci er\n",
        encoding="utf-8",
    )

    assert repair_pronunciation_data.load_yaml_pronunciations(str(yaml_path)) == {
        "词一": "ci yi",
        "词二": "ci er",
    }


def test_build_accumulated_pronunciations_prefers_current_then_existing_yaml(monkeypatch):
    monkeypatch.setattr(repair_pronunciation_data.convert_to_rime, "get_pinyin", lambda word: f"fallback-{word}")

    pronunciations, stats = repair_pronunciation_data.build_accumulated_pronunciations(
        ["现词", "旧词", "缺词"],
        {"现词": "xian ci"},
        {"旧词": "jiu ci"},
    )

    assert pronunciations == {
        "现词": "xian ci",
        "旧词": "jiu ci",
        "缺词": "fallback-缺词",
    }
    assert stats == {
        "from_current": 1,
        "from_existing_yaml": 1,
        "fallback": 1,
        "missing": 0,
    }


def test_repair_data_rebuilds_current_and_accumulated_artifacts(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    scel_path = data_dir / "sogou_network_words.scel"
    scel_path.write_bytes(b"dummy")
    current_txt_path = data_dir / "sogou_network_words_current.txt"
    accumulated_txt_path = data_dir / "sogou_network_words_accumulated.txt"
    current_tsv_path = data_dir / "sogou_network_words_current_pinyin.tsv"
    accumulated_tsv_path = data_dir / "sogou_network_words_accumulated_pinyin.tsv"
    current_yaml_path = data_dir / "luna_pinyin.sogoupopular.current.dict.yaml"
    accumulated_yaml_path = data_dir / "luna_pinyin.sogoupopular.dict.yaml"

    accumulated_txt_path.write_text("现词\n旧词\n", encoding="utf-8")
    accumulated_yaml_path.write_text(
        "# header\n---\nname: test\nversion: \"2026.04.14\"\nsort: by_weight\nuse_preset_vocabulary: true\n...\n\n旧词\tjiu ci\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        repair_pronunciation_data.download_and_convert,
        "parse_scel_file",
        lambda path: [{"word": "现词", "pinyin": "xian ci", "source": "scel"}],
    )
    monkeypatch.setattr(repair_pronunciation_data.convert_to_rime, "get_pinyin", lambda word: "fallback")

    summary = repair_pronunciation_data.repair_data(
        scel_path=str(scel_path),
        current_txt_path=str(current_txt_path),
        accumulated_txt_path=str(accumulated_txt_path),
        current_tsv_path=str(current_tsv_path),
        accumulated_tsv_path=str(accumulated_tsv_path),
        current_yaml_path=str(current_yaml_path),
        accumulated_yaml_path=str(accumulated_yaml_path),
        version="2026.04.14",
    )

    assert summary == {
        "current_words": 1,
        "accumulated_words": 2,
        "from_current": 1,
        "from_existing_yaml": 1,
        "fallback": 0,
        "missing": 0,
    }
    assert current_txt_path.read_text(encoding="utf-8") == "现词\n"
    assert current_tsv_path.read_text(encoding="utf-8") == "现词\txian ci\n"
    assert accumulated_tsv_path.read_text(encoding="utf-8") == "旧词\tjiu ci\n现词\txian ci\n"
    current_yaml = current_yaml_path.read_text(encoding="utf-8")
    accumulated_yaml = accumulated_yaml_path.read_text(encoding="utf-8")
    assert "现词\txian ci" in current_yaml
    assert "现词\txian ci" in accumulated_yaml
    assert "旧词\tjiu ci" in accumulated_yaml
