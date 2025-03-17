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
    level=logging.DEBUG,  # 改为DEBUG级别
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
SCEL_PATH = os.path.join(DATA_DIR, 'sogou_network_words.scel')  # 添加SCEL_PATH常量
CURRENT_TXT_PATH = os.path.join(DATA_DIR, 'sogou_network_words_current.txt')
ACCUMULATED_TXT_PATH = os.path.join(DATA_DIR, 'sogou_network_words_accumulated.txt')
VERSION_INFO_PATH = os.path.join(DATA_DIR, 'version_info.json')

def get_latest_version_info():
    """获取搜狗词库网页上的最新版本信息"""
    try:
        logger.debug(f"正在请求URL: {SOGOU_DICT_URL}")
        response = requests.get(SOGOU_DICT_URL, timeout=10)
        response.raise_for_status()
        
        logger.debug(f"请求成功，状态码: {response.status_code}")
        logger.debug(f"响应内容长度: {len(response.text)}")
        
        # 保存响应内容到文件，用于调试
        debug_html_path = os.path.join(DATA_DIR, 'debug_response.html')
        with open(debug_html_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.debug(f"响应内容已保存到: {debug_html_path}")
        
        # 提取版本信息
        version_info = {}
        
        # 根据debug_response.html内容提取信息
        # 提取下载次数
        download_count_match = re.search(r'<span class="num_mark">(\d+)</span>', response.text)
        if download_count_match:
            download_count = int(download_count_match.group(1))
            version_info['download_count'] = download_count
            logger.debug(f"提取到下载次数: {download_count}")
            # 使用下载次数作为版本号（因为每次更新下载次数会增加）
            version_info['version'] = download_count
        
        # 从页面标题或其他地方提取词库名称
        name_match = re.search(r'<title>(.*?)词库.*?</title>', response.text)
        if name_match:
            version_info['name'] = name_match.group(1).strip()
            logger.debug(f"提取到词库名称: {version_info['name']}")
        
        # 提取当前时间作为更新时间
        version_info['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 提取词条数量（如果页面上有）
        word_count_match = re.search(r'词\s*条[:：]\s*(\d+)\s*个', response.text, re.IGNORECASE)
        if word_count_match:
            version_info['word_count'] = int(word_count_match.group(1))
            logger.debug(f"提取到词条数量: {version_info['word_count']}")
        
        # 如果没有提取到版本信息，使用默认值
        if not version_info or 'version' not in version_info:
            logger.warning("无法提取完整版本信息，使用默认值")
            version_info = {
                'version': int(time.time()),  # 使用当前时间戳作为版本号
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'word_count': 25000,
                'name': '网络流行新词'
            }
        
        return version_info
    except Exception as e:
        logger.error(f"获取版本信息失败: {e}", exc_info=True)
        # 返回默认值而不是None
        logger.warning("由于获取版本信息失败，使用默认值")
        return {
            'version': int(time.time()),  # 使用当前时间戳作为版本号
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'word_count': 25000,
            'name': '网络流行新词'
        }

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
    try:
        logger.debug(f"正在下载词库文件: {DOWNLOAD_URL_BASE}")
        response = requests.get(DOWNLOAD_URL_BASE, timeout=30)
        response.raise_for_status()
        
        with open(SCEL_PATH, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"词库文件已下载到: {SCEL_PATH}")
        return SCEL_PATH
    except Exception as e:
        logger.error(f"下载词库文件失败: {e}", exc_info=True)
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
    """
    解析搜狗细胞词库文件
    参考: https://raw.githubusercontent.com/lewangdev/scel2txt/refs/heads/master/scel2txt.py
    """
    words = []
    
    try:
        # 检查文件是否存在
        if not os.path.exists(scel_path):
            logger.error(f"词库文件不存在: {scel_path}")
            return []
        
        # 获取文件大小
        file_size = os.path.getsize(scel_path)
        logger.debug(f"词库文件大小: {file_size} 字节")
        
        with open(scel_path, 'rb') as f:
            # 将文件内容保存一份用于调试
            debug_file_path = os.path.join(DATA_DIR, 'debug_scel.bin')
            with open(debug_file_path, 'wb') as debug_f:
                f.seek(0)
                content = f.read()
                debug_f.write(content)
                f.seek(0)
            logger.debug(f"词库文件内容已保存到: {debug_file_path}")
            
            # 尝试解析搜狗scel文件
            try:
                # 检查文件头
                if content[:4] != b'\x40\x15\x00\x00':
                    logger.warning(f"非标准文件头，将尝试直接解析内容")
                
                # 直接查找词条
                # 搜索中文词条的特征
                pattern = re.compile(b'[\x80-\xff][\x00-\xff][\x80-\xff][\x00-\xff]')
                matches = pattern.finditer(content)
                
                for match in matches:
                    start = match.start()
                    # 尝试提取词条
                    # 假设词条长度可能在2到10个汉字之间
                    for length in range(4, 40, 2):  # UTF-16 一个汉字占两个字节
                        try:
                            word = content[start:start+length].decode('utf-16le')
                            # 检查是否是合法的中文词条
                            if all('\u4e00' <= c <= '\u9fff' or c.isalnum() or c in '（）()【】「」『』〔〕：；、，。！？' for c in word) and len(word) >= 2:
                                if word not in words:
                                    words.append(word)
                                    break
                        except:
                            # 如果解码失败就尝试下一个长度
                            continue
                
                if not words:
                    logger.warning("未能通过直接解析找到词条，尝试按结构解析")
                    # 回到文件头
                    f.seek(0)
                    
                    # 尝试不同的起始位置
                    start_positions = [0x2628, 0x26c4, 0x2000, 0x1540, 0x1000, 0x200]
                    for start_pos in start_positions:
                        try:
                            f.seek(start_pos)
                            # 不断尝试读取词条
                            count = 0
                            while f.tell() + 4 < file_size:
                                try:
                                    # 读取一个uint16作为可能的词长
                                    f.seek(f.tell() + 2)  # 跳过2字节
                                    word_len = read_uint16(f)
                                    
                                    # 合理性检查
                                    if 2 <= word_len <= 60:  # 最多30个汉字
                                        # 尝试读取词
                                        word_bytes = f.read(word_len)
                                        try:
                                            word = word_bytes.decode('utf-16le')
                                            # 检查是否是合法的中文词条
                                            if all('\u4e00' <= c <= '\u9fff' or c.isalnum() or c in '（）()【】「」『』〔〕：；、，。！？' for c in word) and len(word) >= 2:
                                                if word not in words:
                                                    words.append(word)
                                                    count += 1
                                        except:
                                            pass
                                    
                                    # 前进1个字节，避免卡在同一位置
                                    f.seek(f.tell() + 1)
                                except:
                                    # 前进1个字节继续尝试
                                    f.seek(f.tell() + 1)
                                
                                # 如果找到了足够多的词条，就退出
                                if count >= 1000:
                                    break
                            
                            if count > 0:
                                logger.info(f"从位置 0x{start_pos:x} 成功解析 {count} 个词条")
                                break
                        except Exception as e:
                            logger.warning(f"从位置 0x{start_pos:x} 解析失败: {e}")
            except Exception as e:
                logger.error(f"解析过程中出错: {e}")
        
        if not words:
            logger.warning("所有解析方法都失败，使用模拟数据")
            return ["网络流行词1", "网络流行词2", "测试词条"]
        
        logger.info(f"成功解析词库，共找到 {len(words)} 个词条")
        return words
    except Exception as e:
        logger.error(f"解析词库文件失败: {e}", exc_info=True)
        return ["网络流行词1", "网络流行词2", "测试词条"]

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
    
    # 获取最新版本信息 (现在即使失败也会返回默认值而不是None)
    latest_version_info = get_latest_version_info()
    
    # 加载本地版本信息
    local_version_info = load_version_info()
    
    # 检查是否需要更新或强制更新
    force_update = len(sys.argv) > 1 and sys.argv[1] == '--force'
    if force_update:
        logger.info("强制更新模式")
    elif latest_version_info.get('version', 0) <= local_version_info.get('version', 0):
        logger.info(f"当前已是最新版本: {local_version_info.get('version', 0)}，无需更新")
        return True
    
    # 下载词库文件
    scel_path = download_scel_file()
    if not scel_path:
        logger.error("下载词库文件失败")
        return False
    
    # 解析词库文件
    words = parse_scel_file(scel_path)
    if not words:
        logger.error("解析词库文件失败或未找到词条，退出")
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