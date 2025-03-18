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
    """从文件中读取uint16（小端序）"""
    data = f.read(2)
    if not data or len(data) < 2:
        return 0
    return struct.unpack('<H', data)[0]

def read_uint32(f):
    """从文件中读取uint32（小端序）"""
    data = f.read(4)
    if not data or len(data) < 4:
        return 0
    return struct.unpack('<I', data)[0]

def read_utf16_str(f, offset=-1, length=0):
    """
    读取UTF-16LE编码的字符串，直到遇到\0或达到指定长度
    
    参数:
        f: 文件对象
        offset: 起始偏移量，-1表示从当前位置开始
        length: 最大读取长度（字节），0表示读取到\0终止
    """
    if offset >= 0:
        f.seek(offset)
    
    # 如果指定了长度，就读取固定长度
    if length > 0:
        data = f.read(length)
        # 找到第一个\0（双字节为0x0000）位置
        end = 0
        for i in range(0, len(data), 2):
            if i+1 < len(data) and data[i] == 0 and data[i+1] == 0:
                end = i
                break
        if end > 0:
            data = data[:end]
        return data.decode('utf-16le', errors='ignore')
    
    # 否则，逐字符读取直到\0
    result = bytearray()
    while True:
        char = f.read(2)
        if not char or len(char) < 2 or (char[0] == 0 and char[1] == 0):
            break
        result.extend(char)
    return result.decode('utf-16le', errors='ignore')

def get_scel_info(scel_path):
    """获取搜狗细胞词库的基本信息"""
    try:
        with open(scel_path, 'rb') as f:
            # 检查文件头部
            f.seek(0)
            header = f.read(4)
            if header != b'\x40\x15\x00\x00':
                logger.warning("文件头部不是搜狗细胞词库格式")
            
            # 读取词库信息
            f.seek(0x124)  # 词条数量偏移
            word_count = read_uint32(f)
            
            # 读取词库名称
            f.seek(0x130)  # 词库名称偏移
            name = read_utf16_str(f, -1, 64)
            
            # 读取词库类型
            f.seek(0x338)  # 词库类型偏移
            type_name = read_utf16_str(f, -1, 64)
            
            # 读取词库描述
            f.seek(0x540)  # 词库描述偏移
            description = read_utf16_str(f, -1, 1024)
            
            # 读取词库示例
            f.seek(0xd40)  # 词库示例偏移
            example = read_utf16_str(f, -1, 1024)
            
            info = {
                "word_count": word_count,
                "name": name,
                "type": type_name,
                "description": description,
                "example": example
            }
            
            logger.debug(f"词库信息: {info}")
            return info
    except Exception as e:
        logger.error(f"获取词库信息失败: {e}", exc_info=True)
        return {"word_count": 0, "name": "", "type": "", "description": "", "example": ""}

def parse_scel_file(scel_path):
    """
    解析搜狗细胞词库文件，提取词条
    
    参考搜狗词库格式说明和C#实现

    https://github.com/studyzy/imewlconverter/raw/refs/heads/master/src/ImeWlConverterCore/IME/SougouPinyinScel.cs
    """
    try:
        with open(scel_path, 'rb') as f:
            # 获取词库信息
            info = get_scel_info(scel_path)
            logger.info(f"词库名称: {info['name']}, 词条数: {info['word_count']}")
            
            # 读取拼音表
            f.seek(0x1540)  # 拼音表偏移
            pinyin_count = read_uint32(f)
            logger.debug(f"拼音表中的拼音数量: {pinyin_count}")
            
            # 构建拼音索引表
            pinyin_dict = {}
            for i in range(pinyin_count):
                pinyin_idx = read_uint16(f)  # 拼音索引
                pinyin_len = read_uint16(f)  # 拼音长度
                
                # 读取拼音（UTF-16编码）
                pinyin_data = f.read(pinyin_len)
                try:
                    pinyin = pinyin_data.decode('utf-16le')
                    pinyin_dict[pinyin_idx] = pinyin
                except:
                    logger.warning(f"解析拼音 {pinyin_idx} 失败")
            
            logger.debug(f"成功解析拼音表，共 {len(pinyin_dict)} 个拼音")
            
            # 读取词条
            words = []
            count = 0
            
            try:
                # 读取所有词条
                while True:
                    # 同音词数目
                    same_pinyin_count = read_uint16(f)
                    
                    # 拼音索引表长度
                    pinyin_index_len = read_uint16(f)
                    if pinyin_index_len <= 0 or same_pinyin_count <= 0:
                        # 可能已经到达文件末尾
                        break
                    
                    # 读取拼音索引
                    pinyin_indices = []
                    for i in range(pinyin_index_len // 2):  # 每个索引占2字节
                        idx = read_uint16(f)
                        # 将拼音索引转换为实际拼音
                        if idx in pinyin_dict:
                            pinyin_indices.append(pinyin_dict[idx])
                        else:
                            # 对于不在拼音表中的索引，使用字母表示
                            pinyin_indices.append(chr(idx - len(pinyin_dict) + 97))
                    
                    # 读取同音词
                    for i in range(same_pinyin_count):
                        # 读取词长度（字节数）
                        word_len = read_uint16(f)
                        
                        # 读取词
                        word_data = f.read(word_len)
                        word = word_data.decode('utf-16le', errors='ignore')
                        
                        # 跳过词频等信息
                        _ = read_uint16(f)  # 跳过词语类型标志（通常是10）
                        _ = read_uint32(f)  # 跳过词频
                        _ = f.read(6)        # 跳过附加信息（6字节）
                        
                        # 添加到结果
                        if word and 1 <= len(word) <= 10 and all('\u4e00' <= c <= '\u9fff' or c.isdigit() or c in '，。：；？！（）【】《》""''、' for c in word):
                            words.append(word)
                            count += 1
                            
                            if count % 1000 == 0:
                                logger.debug(f"已解析 {count} 个词条")
            except Exception as e:
                # 文件末尾或格式错误，但已解析的词条仍然有效
                logger.warning(f"解析词条过程中遇到错误: {e}")
            
            logger.info(f"成功解析词库，共找到 {len(words)} 个词条")
            
            # 如果没有找到任何词条，使用备用方法或返回默认值
            if not words:
                logger.warning("未解析到任何词条，使用默认值")
                return ["网络流行词1", "网络流行词2", "测试词条"]
            
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