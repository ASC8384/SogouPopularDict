#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import struct
import tempfile
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('sogou_dict')

# 常量定义
SOGOU_DICT_URL = 'https://pinyin.sogou.com/dict/detail/index/4'
DOWNLOAD_URL_BASE = 'https://pinyin.sogou.com/d/dict/download_cell.php?id=4&name=%E7%BD%91%E7%BB%9C%E6%B5%81%E8%A1%8C%E6%96%B0%E8%AF%8D&f=detail'
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CURRENT_TXT_PATH = os.path.join(DATA_DIR, 'sogou_network_words_current.txt')
ACCUMULATED_TXT_PATH = os.path.join(DATA_DIR, 'sogou_network_words_accumulated.txt')
VERSION_INFO_PATH = os.path.join(DATA_DIR, 'version_info.json')

def get_latest_version_info():
    """获取搜狗词库网页上的最新版本信息"""
    try:
        response = requests.get(SOGOU_DICT_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取版本信息
        version_info = {}
        info_items = soup.select('.detail_info dl dd')
        
        if info_items and len(info_items) >= 4:
            # 提取词条数量
            word_count_text = info_items[0].text.strip()
            word_count_match = re.search(r'(\d+)', word_count_text)
            if word_count_match:
                version_info['word_count'] = int(word_count_match.group(1))
            
            # 提取更新时间
            update_time_text = info_items[2].text.strip()
            version_info['update_time'] = update_time_text
            
            # 提取版本号
            version_text = info_items[3].text.strip()
            version_match = re.search(r'第(\d+)个版本', version_text)
            if version_match:
                version_info['version'] = int(version_match.group(1))
                
        return version_info
    except Exception as e:
        logger.error(f"获取版本信息失败: {e}")
        return None

def save_version_info(version_info):
    """保存版本信息到文件"""
    try:
        with open(VERSION_INFO_PATH, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)
        logger.info(f"版本信息已保存: {version_info}")
    except Exception as e:
        logger.error(f"保存版本信息失败: {e}")

def load_version_info():
    """从文件加载版本信息"""
    if not os.path.exists(VERSION_INFO_PATH):
        return {'version': 0, 'update_time': '', 'word_count': 0}
    
    try:
        with open(VERSION_INFO_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载版本信息失败: {e}")
        return {'version': 0, 'update_time': '', 'word_count': 0}

def download_scel_file():
    """下载搜狗细胞词库文件"""
    scel_path = os.path.join(tempfile.gettempdir(), 'sogou_network_words.scel')
    
    try:
        response = requests.get(DOWNLOAD_URL_BASE, timeout=30)
        response.raise_for_status()
        
        with open(scel_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"词库文件已下载到: {scel_path}")
        return scel_path
    except Exception as e:
        logger.error(f"下载词库文件失败: {e}")
        return None

def read_uint16(f):
    """从文件中读取uint16"""
    return struct.unpack('<H', f.read(2))[0]

def read_uint32(f):
    """从文件中读取uint32"""
    return struct.unpack('<I', f.read(4))[0]

def read_string(f, encoding='utf-16le'):
    """从文件中读取字符串"""
    length = read_uint16(f)
    string = f.read(length)
    return string.decode(encoding)

def parse_scel_file(scel_path):
    """解析搜狗细胞词库文件"""
    words = []
    
    try:
        with open(scel_path, 'rb') as f:
            # 跳过文件头
            f.seek(0x2628)
            
            while True:
                # 拼音表长度
                py_count = read_uint16(f)
                
                # 跳过拼音表
                f.seek(py_count * 2, 1)
                
                # 词组长度
                word_len = read_uint16(f)
                
                # 词组
                word = f.read(word_len).decode('utf-16le')
                
                # 跳过扩展信息
                ext_len = read_uint16(f)
                f.seek(ext_len, 1)
                
                words.append(word)
                
                # 判断是否到文件尾
                try:
                    read_uint16(f)
                    f.seek(-2, 1)  # 回退2字节
                except:
                    break
        
        logger.info(f"成功解析词库，共 {len(words)} 个词条")
        return words
    except Exception as e:
        logger.error(f"解析词库文件失败: {e}")
        return []

def save_to_txt(words, file_path):
    """保存词条到txt文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for word in words:
                f.write(f"{word}\n")
        logger.info(f"词条已保存到: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存词条失败: {e}")
        return False

def load_accumulated_words():
    """加载累积的词条"""
    if not os.path.exists(ACCUMULATED_TXT_PATH):
        return set()
    
    try:
        with open(ACCUMULATED_TXT_PATH, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        logger.error(f"加载累积词条失败: {e}")
        return set()

def update_accumulated_words(current_words):
    """更新累积的词条"""
    accumulated_words = load_accumulated_words()
    old_count = len(accumulated_words)
    
    # 合并新词
    accumulated_words.update(current_words)
    new_count = len(accumulated_words)
    
    # 保存
    try:
        with open(ACCUMULATED_TXT_PATH, 'w', encoding='utf-8') as f:
            for word in sorted(accumulated_words):
                f.write(f"{word}\n")
        
        logger.info(f"累积词条已更新: 原有 {old_count} 个，现有 {new_count} 个，新增 {new_count - old_count} 个")
        return True
    except Exception as e:
        logger.error(f"更新累积词条失败: {e}")
        return False

def main():
    """主函数"""
    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 获取最新版本信息
    latest_version_info = get_latest_version_info()
    if not latest_version_info:
        logger.error("无法获取最新版本信息，退出")
        return False
    
    # 加载本地版本信息
    local_version_info = load_version_info()
    
    # 检查是否需要更新
    if latest_version_info.get('version', 0) <= local_version_info.get('version', 0):
        logger.info(f"当前已是最新版本: {local_version_info.get('version', 0)}，无需更新")
        return True
    
    # 下载词库文件
    scel_path = download_scel_file()
    if not scel_path:
        return False
    
    # 解析词库文件
    words = parse_scel_file(scel_path)
    if not words:
        return False
    
    # 保存当前词条到txt
    if not save_to_txt(words, CURRENT_TXT_PATH):
        return False
    
    # 更新累积词条
    if not update_accumulated_words(words):
        return False
    
    # 保存最新版本信息
    save_version_info(latest_version_info)
    
    logger.info("词库更新完成")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 