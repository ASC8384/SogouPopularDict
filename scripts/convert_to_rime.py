#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pypinyin import lazy_pinyin, Style

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('rime_converter')

# 常量定义
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CURRENT_TXT_PATH = os.path.join(DATA_DIR, 'sogou_network_words_current.txt')
ACCUMULATED_TXT_PATH = os.path.join(DATA_DIR, 'sogou_network_words_accumulated.txt')
CURRENT_PINYIN_PATH = os.path.join(DATA_DIR, 'sogou_network_words_current_pinyin.tsv')
ACCUMULATED_PINYIN_PATH = os.path.join(DATA_DIR, 'sogou_network_words_accumulated_pinyin.tsv')
RIME_CURRENT_PATH = os.path.join(DATA_DIR, 'luna_pinyin.sogoupopular.current.dict.yaml')
RIME_ACCUMULATED_PATH = os.path.join(DATA_DIR, 'luna_pinyin.sogoupopular.dict.yaml')
VERSION_INFO_PATH = os.path.join(DATA_DIR, 'version_info.json')


def load_words_from_txt(txt_path):
    """从TXT文件加载词条"""
    if not os.path.exists(txt_path):
        logger.error(f"文件不存在: {txt_path}")
        return []

    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"加载词条失败: {e}")
        return []


def load_pronunciations_from_tsv(tsv_path):
    """从 TSV 文件加载词到拼音的映射。"""
    if not os.path.exists(tsv_path):
        logger.error(f"拼音映射文件不存在: {tsv_path}")
        return {}

    try:
        pronunciations = {}
        with open(tsv_path, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split('\t', 1)
                if len(parts) != 2:
                    logger.error(f"拼音映射行格式无效: {line}")
                    return {}
                word, pinyin = parts
                if word and pinyin:
                    pronunciations[word] = pinyin.strip()
        return pronunciations
    except Exception as e:
        logger.error(f"加载拼音映射失败: {e}")
        return {}


def get_pinyin(word):
    """保留为受控 fallback helper。"""
    try:
        return ' '.join(lazy_pinyin(word, style=Style.NORMAL))
    except Exception as e:
        logger.warning(f"获取拼音失败: {word}, {e}")
        return ''


def load_version_info():
    """从文件加载版本信息"""
    if not os.path.exists(VERSION_INFO_PATH):
        return {}

    try:
        with open(VERSION_INFO_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载版本信息失败: {e}")
        return {}


def format_version_from_version_info(version_info):
    """从版本信息中生成 Rime 版本号"""
    update_time = version_info.get('update_time', '')
    if update_time:
        try:
            return datetime.strptime(update_time, '%Y-%m-%d %H:%M:%S').strftime('%Y.%m.%d')
        except ValueError:
            logger.warning(f"无法解析更新时间: {update_time}")

    return datetime.now().strftime('%Y.%m.%d')


def convert_to_rime_yaml(words, pronunciations, output_path, version=None):
    """将词条和稳定拼音映射转换为Rime YAML格式"""
    yaml_version = version or datetime.now().strftime('%Y.%m.%d')

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('# Rime dictionary\n')
            f.write('# encoding: utf-8\n')
            f.write('#\n')
            f.write('# Luna Pinyin Extended Dictionary（明月拼音扩充词库）\n')
            f.write('# 网络流行新词（当前版本）\n' if 'current' in output_path else '# 网络流行新词（累积版本）\n')
            f.write('#\n')
            f.write('# https://github.com/ASC8384/SogouPopularDict\n')
            f.write('# mailto:ASC_8384atfoxmail.com\n')
            f.write('#\n')
            f.write('# 部署位置：\n')
            f.write('# ~/.config/ibus/rime  (Linux)\n')
            f.write('# ~/Library/Rime  (Mac OS)\n')
            f.write('# %APPDATA%\\Rime  (Windows)\n')
            f.write('#\n')
            f.write('# 重新部署即可\n')
            f.write('#\n')
            f.write('---\n')

            name = 'luna_pinyin.sogoupopular.current' if 'current' in output_path else 'luna_pinyin.sogoupopular'
            f.write(f'name: {name}\n')
            f.write(f'version: "{yaml_version}"\n')
            f.write('sort: by_weight\n')
            f.write('use_preset_vocabulary: true\n')
            f.write('...\n\n')

            for word in words:
                pinyin = pronunciations.get(word, '').strip()
                if not pinyin:
                    logger.error(f'词条缺少拼音映射: {word}')
                    return False
                f.write(f'{word}\t{pinyin}\n')

        logger.info(f'已生成Rime词库: {output_path}')
        return True
    except Exception as e:
        logger.error(f'生成Rime词库失败: {e}')
        return False


def generate_rime_dict(txt_path, tsv_path, output_path, version=None):
    """从 txt 与 tsv 生成 Rime YAML。"""
    words = load_words_from_txt(txt_path)
    if not words:
        logger.warning(f'词库为空或不存在: {txt_path}')
        return False

    pronunciations = load_pronunciations_from_tsv(tsv_path)
    if not pronunciations:
        logger.warning(f'拼音映射为空或不存在: {tsv_path}')
        return False

    return convert_to_rime_yaml(words, pronunciations, output_path, version=version)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='将TXT+TSV格式词库转换为Rime YAML格式')
    parser.add_argument('--current-only', action='store_true', help='仅转换当前词库')
    parser.add_argument('--accumulated-only', action='store_true', help='仅转换累积词库')
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    success = True
    version_info = load_version_info()
    yaml_version = format_version_from_version_info(version_info)

    if not args.accumulated_only:
        if not generate_rime_dict(CURRENT_TXT_PATH, CURRENT_PINYIN_PATH, RIME_CURRENT_PATH, version=yaml_version):
            success = False

    if not args.current_only:
        if not generate_rime_dict(ACCUMULATED_TXT_PATH, ACCUMULATED_PINYIN_PATH, RIME_ACCUMULATED_PATH, version=yaml_version):
            success = False

    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
