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
RIME_CURRENT_PATH = os.path.join(DATA_DIR, 'luna_pinyin.sogoupopular.current.dict.yaml')
RIME_ACCUMULATED_PATH = os.path.join(DATA_DIR, 'luna_pinyin.sogoupopular.dict.yaml')

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
    now = datetime.now().strftime('%Y.%m.%d')
    
    # 写入YAML文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入YAML头部
            f.write("# Rime dictionary\n")
            f.write("# encoding: utf-8\n")
            f.write("#\n")
            f.write("# Luna Pinyin Extended Dictionary（明月拼音扩充词库）\n")
            f.write("# 网络流行新词（当前版本）\n" if "current" in output_path else "# 网络流行新词（累积版本）\n")
            f.write("#\n")
            f.write("# https://github.com/ASC8384/SogouPopularDict\n")
            f.write("# mailto:ASC_8384atfoxmail.com\n")
            f.write("#\n")
            f.write("# 部署位置：\n")
            f.write("# ~/.config/ibus/rime  (Linux)\n")
            f.write("# ~/Library/Rime  (Mac OS)\n")
            f.write("# %APPDATA%\\Rime  (Windows)\n")
            f.write("#\n")
            f.write("# 重新部署即可\n")
            f.write("#\n")
            f.write("---\n")
            
            # 根据是当前版本还是累积版本设置不同的name
            name = "luna_pinyin.sogoupopular.current" if "current" in output_path else "luna_pinyin.sogoupopular"
            
            f.write(f"name: {name}\n")
            f.write(f"version: \"{now}\"\n")
            f.write("sort: by_weight\n")
            f.write("use_preset_vocabulary: true\n")
            
            # 写入分隔符
            f.write("...\n\n")
            
            # 写入词条 - 移除权重计算
            for word in words:
                pinyin = get_pinyin(word)
                if pinyin:
                    # 不再计算权重，直接写入词条和拼音
                    f.write(f"{word}\t{pinyin}\n")
        
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