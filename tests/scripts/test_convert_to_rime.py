import scripts.convert_to_rime as convert_to_rime


def test_convert_to_rime_yaml_uses_supplied_version(tmp_path):
    output_path = tmp_path / "out.current.dict.yaml"

    assert convert_to_rime.convert_to_rime_yaml(
        ["测试词"],
        str(output_path),
        version="2025.05.12",
    ) is True

    content = output_path.read_text(encoding="utf-8")
    assert 'version: "2025.05.12"' in content


def test_load_words_from_txt_filters_blank_lines(tmp_path):
    txt_path = tmp_path / "words.txt"
    txt_path.write_text("词一\n\n词二\n", encoding="utf-8")

    assert convert_to_rime.load_words_from_txt(str(txt_path)) == ["词一", "词二"]


def test_format_version_from_version_info_uses_update_time():
    version_info = {
        "version": 1747021217,
        "update_time": "2025-05-12 03:40:17",
        "word_count": 25000,
        "name": "网络流行新词",
    }

    assert convert_to_rime.format_version_from_version_info(version_info) == "2025.05.12"
