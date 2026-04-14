import scripts.convert_to_rime as convert_to_rime


def test_convert_to_rime_yaml_uses_supplied_version_and_pronunciations(tmp_path):
    output_path = tmp_path / "out.current.dict.yaml"

    assert convert_to_rime.convert_to_rime_yaml(
        ["测试词"],
        {"测试词": "ce shi ci"},
        str(output_path),
        version="2025.05.12",
    ) is True

    content = output_path.read_text(encoding="utf-8")
    assert 'version: "2025.05.12"' in content
    assert "测试词\tce shi ci" in content


def test_convert_to_rime_yaml_returns_false_when_pronunciation_missing(tmp_path):
    output_path = tmp_path / "out.dict.yaml"

    assert convert_to_rime.convert_to_rime_yaml(
        ["缺拼音词"],
        {},
        str(output_path),
        version="2025.05.12",
    ) is False


def test_load_words_from_txt_filters_blank_lines(tmp_path):
    txt_path = tmp_path / "words.txt"
    txt_path.write_text("词一\n\n词二\n", encoding="utf-8")

    assert convert_to_rime.load_words_from_txt(str(txt_path)) == ["词一", "词二"]


def test_load_pronunciations_from_tsv_reads_mapping(tmp_path):
    tsv_path = tmp_path / "words.tsv"
    tsv_path.write_text("词一\tyi\n词二\ter\n", encoding="utf-8")

    assert convert_to_rime.load_pronunciations_from_tsv(str(tsv_path)) == {
        "词一": "yi",
        "词二": "er",
    }


def test_generate_rime_dict_uses_txt_order_and_tsv_pronunciations(tmp_path):
    txt_path = tmp_path / "words.txt"
    tsv_path = tmp_path / "words.tsv"
    output_path = tmp_path / "out.dict.yaml"

    txt_path.write_text("词二\n词一\n", encoding="utf-8")
    tsv_path.write_text("词一\tyi\n词二\ter\n", encoding="utf-8")

    assert convert_to_rime.generate_rime_dict(
        str(txt_path),
        str(tsv_path),
        str(output_path),
        version="2025.05.12",
    ) is True

    content = output_path.read_text(encoding="utf-8")
    assert content.index("词二\ter") < content.index("词一\tyi")


def test_generate_rime_dict_returns_false_when_tsv_missing_word(tmp_path):
    txt_path = tmp_path / "words.txt"
    tsv_path = tmp_path / "words.tsv"
    output_path = tmp_path / "out.dict.yaml"

    txt_path.write_text("词一\n词二\n", encoding="utf-8")
    tsv_path.write_text("词一\tyi\n", encoding="utf-8")

    assert convert_to_rime.generate_rime_dict(
        str(txt_path),
        str(tsv_path),
        str(output_path),
        version="2025.05.12",
    ) is False
