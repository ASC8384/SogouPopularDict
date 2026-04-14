#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os

from scripts import convert_to_rime, download_and_convert


def load_yaml_pronunciations(yaml_path):
    """从现有 Rime YAML 中回收 `词 -> 拼音`，供历史 accumulated 词做冻结回填。"""
    pronunciations = {}
    if not os.path.exists(yaml_path):
        return pronunciations

    with open(yaml_path, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith('#') or line in {'---', '...'} or ':' in line and '\t' not in line:
                continue
            parts = line.split('\t', 1)
            if len(parts) == 2:
                word, pinyin = parts
                if word and pinyin:
                    pronunciations[word] = pinyin.strip()
    return pronunciations


def build_accumulated_pronunciations(accumulated_words, current_pronunciations, existing_yaml_pronunciations):
    """按 current SCEL -> 现有 YAML -> fallback 的优先级为 accumulated 构建稳定拼音映射。"""
    pronunciations = {}
    stats = {
        'from_current': 0,
        'from_existing_yaml': 0,
        'fallback': 0,
        'missing': 0,
    }

    for word in accumulated_words:
        if word in current_pronunciations:
            pronunciations[word] = current_pronunciations[word]
            stats['from_current'] += 1
            continue

        if word in existing_yaml_pronunciations:
            pronunciations[word] = existing_yaml_pronunciations[word]
            stats['from_existing_yaml'] += 1
            continue

        fallback = convert_to_rime.get_pinyin(word)
        if fallback:
            pronunciations[word] = fallback
            stats['fallback'] += 1
        else:
            stats['missing'] += 1

    return pronunciations, stats


def repair_data(
    scel_path,
    current_txt_path,
    accumulated_txt_path,
    current_tsv_path,
    accumulated_tsv_path,
    current_yaml_path,
    accumulated_yaml_path,
    version,
):
    entries = download_and_convert.parse_scel_file(scel_path)
    if not entries:
        raise RuntimeError('未能从 SCEL 解析出词条，无法修复数据')

    current_words = download_and_convert.extract_words(entries)
    current_pronunciations = download_and_convert.build_pronunciation_map(entries)

    if not download_and_convert.save_to_txt(entries, current_txt_path):
        raise RuntimeError('写入 current txt 失败')
    if not download_and_convert.save_pronunciations_to_tsv(current_pronunciations, current_tsv_path):
        raise RuntimeError('写入 current tsv 失败')
    if not convert_to_rime.convert_to_rime_yaml(current_words, current_pronunciations, current_yaml_path, version=version):
        raise RuntimeError('生成 current YAML 失败')

    accumulated_words = convert_to_rime.load_words_from_txt(accumulated_txt_path)
    existing_yaml_pronunciations = load_yaml_pronunciations(accumulated_yaml_path)
    accumulated_pronunciations, stats = build_accumulated_pronunciations(
        accumulated_words,
        current_pronunciations,
        existing_yaml_pronunciations,
    )

    if not download_and_convert.save_pronunciations_to_tsv(accumulated_pronunciations, accumulated_tsv_path):
        raise RuntimeError('写入 accumulated tsv 失败')
    if not convert_to_rime.convert_to_rime_yaml(accumulated_words, accumulated_pronunciations, accumulated_yaml_path, version=version):
        raise RuntimeError('生成 accumulated YAML 失败')

    return {
        'current_words': len(current_words),
        'accumulated_words': len(accumulated_words),
        **stats,
    }


def main():
    parser = argparse.ArgumentParser(description='修复当前仓库中的拼音 sidecar 与 YAML 数据')
    parser.add_argument('--scel-path', default=download_and_convert.SCEL_PATH)
    parser.add_argument('--current-txt-path', default=download_and_convert.CURRENT_TXT_PATH)
    parser.add_argument('--accumulated-txt-path', default=download_and_convert.ACCUMULATED_TXT_PATH)
    parser.add_argument('--current-tsv-path', default=download_and_convert.CURRENT_PINYIN_PATH)
    parser.add_argument('--accumulated-tsv-path', default=download_and_convert.ACCUMULATED_PINYIN_PATH)
    parser.add_argument('--current-yaml-path', default=convert_to_rime.RIME_CURRENT_PATH)
    parser.add_argument('--accumulated-yaml-path', default=convert_to_rime.RIME_ACCUMULATED_PATH)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()

    summary = repair_data(
        scel_path=args.scel_path,
        current_txt_path=args.current_txt_path,
        accumulated_txt_path=args.accumulated_txt_path,
        current_tsv_path=args.current_tsv_path,
        accumulated_tsv_path=args.accumulated_tsv_path,
        current_yaml_path=args.current_yaml_path,
        accumulated_yaml_path=args.accumulated_yaml_path,
        version=args.version,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
