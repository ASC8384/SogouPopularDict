#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import yaml
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
RIME_CURRENT_PATH = os.path.join(DATA_DIR, 'sogou_network_words_current.dict.yaml')
RIME_ACCUMULATED_PATH = os.path.join(DATA_DIR, 'sogou_network_words_accumulated.dict.yaml')

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

def get_pinyin(word):
    """获取词语的拼音"""
    try:
        # 使用pypinyin获取拼音，并用空格连接
        return ' '.join(lazy_pinyin(word, style=Style.NORMAL))
    except Exception as e:
        logger.warning(f"获取拼音失败: {word}, {e}")
        return ''

def convert_to_rime_yaml(words, output_path, dict_name):
    """将词条转换为Rime YAML格式"""
    # 准备YAML头部
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = {
        'name': dict_name,
        'version': now,
        'sort': 'by_weight',
        'use_preset_vocabulary': False,
        'import_tables': [],
        'columns': ['text', 'code', 'weight'],
        'encoder': {
            'rules': {
                'xlit/ABCDEFGHIJKLMNOPQRSTUVWXYZ/abcdefghijklmnopqrstuvwxyz/',
            }
        }
    }
    
    # 准备词条
    entries = []
    for i, word in enumerate(words):
        pinyin = get_pinyin(word)
        if pinyin:
            # 权重从高到低排序，新词条权重高
            weight = len(words) - i
            entries.append(f"{word}\t{pinyin}\t{weight}")
    
    # 写入YAML文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入YAML头部
            f.write("# Rime dictionary\n")
            f.write("# encoding: utf-8\n")
            f.write("#\n")
            f.write(f"# {dict_name}\n")
            f.write(f"# 自动生成于 {now}\n")
            f.write("#\n\n")
            
            # 写入YAML配置
            yaml.dump(header, f, allow_unicode=True, default_flow_style=False)
            
            # 写入分隔符
            f.write("\n...\n\n")
            
            # 写入词条
            for entry in entries:
                f.write(f"{entry}\n")
        
        logger.info(f"已生成Rime词库: {output_path}")
        return True
    except Exception as e:
        logger.error(f"生成Rime词库失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='将TXT格式词库转换为Rime YAML格式')
    parser.add_argument('--current-only', action='store_true', help='仅转换当前词库')
    parser.add_argument('--accumulated-only', action='store_true', help='仅转换累积词库')
    args = parser.parse_args()
    
    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    
    success = True
    
    # 转换当前词库
    if not args.accumulated_only:
        words = load_words_from_txt(CURRENT_TXT_PATH)
        if words:
            if not convert_to_rime_yaml(words, RIME_CURRENT_PATH, '搜狗网络流行新词（当前版本）'):
                success = False
        else:
            logger.warning(f"当前词库为空或不存在")
    
    # 转换累积词库
    if not args.current_only:
        words = load_words_from_txt(ACCUMULATED_TXT_PATH)
        if words:
            if not convert_to_rime_yaml(words, RIME_ACCUMULATED_PATH, '搜狗网络流行新词（累积版本）'):
                success = False
        else:
            logger.warning(f"累积词库为空或不存在")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 