#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import html
import requests
from datetime import datetime
import struct
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
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
SCEL_PATH = os.path.join(DATA_DIR, 'sogou_network_words.scel')
CURRENT_TXT_PATH = os.path.join(DATA_DIR, 'sogou_network_words_current.txt')
ACCUMULATED_TXT_PATH = os.path.join(DATA_DIR, 'sogou_network_words_accumulated.txt')
CURRENT_PINYIN_PATH = os.path.join(DATA_DIR, 'sogou_network_words_current_pinyin.tsv')
ACCUMULATED_PINYIN_PATH = os.path.join(DATA_DIR, 'sogou_network_words_accumulated_pinyin.tsv')
VERSION_INFO_PATH = os.path.join(DATA_DIR, 'version_info.json')

STATUS_UPDATED = 'updated'
STATUS_NO_UPDATE = 'no_update'
STATUS_ERROR = 'error'


def get_latest_version_info():
    """获取搜狗词库网页上的最新版本信息"""
    try:
        logger.debug(f"正在请求URL: {SOGOU_DICT_URL}")
        response = requests.get(SOGOU_DICT_URL, timeout=10)
        response.raise_for_status()

        logger.debug(f"请求成功，状态码: {response.status_code}")
        logger.debug(f"响应内容长度: {len(response.text)}")

        debug_html_path = os.path.join(DATA_DIR, 'debug_response.html')
        with open(debug_html_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.debug(f"响应内容已保存到: {debug_html_path}")

        page_text = html.unescape(response.text)
        version_info = {}

        download_count_match = re.search(r'<span class="num_mark">(\d+)</span>', response.text)
        if download_count_match:
            download_count = int(download_count_match.group(1))
            version_info['download_count'] = download_count
            logger.debug(f"提取到下载次数: {download_count}")

        version_match = re.search(r'版\s*本[:：]\s*第\s*(\d+)\s*个版本', page_text)
        if version_match:
            version_info['version'] = int(version_match.group(1))
            logger.debug(f"提取到页面版本号: {version_info['version']}")

        name_match = re.search(r'<title>(.*?)词库.*?</title>', response.text)
        if name_match:
            version_info['name'] = name_match.group(1).strip()
            logger.debug(f"提取到词库名称: {version_info['name']}")

        update_time_match = re.search(r'更\s*新[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2})', page_text)
        if update_time_match:
            version_info['update_time'] = update_time_match.group(1)
        else:
            version_info['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        word_count_match = re.search(r'词\s*条[:：]\s*(\d+)\s*个', page_text, re.IGNORECASE)
        if word_count_match:
            version_info['word_count'] = int(word_count_match.group(1))
            logger.debug(f"提取到词条数量: {version_info['word_count']}")

        if not version_info or 'version' not in version_info:
            logger.warning("无法提取完整版本信息")
            return None

        return version_info
    except Exception as e:
        logger.error(f"获取版本信息失败: {e}", exc_info=True)
        logger.warning("由于获取版本信息失败，返回空结果")
        return None


def normalize_version_info(version_info):
    """归一化版本信息，确保比较字段语义一致"""
    if not version_info:
        return None

    normalized = dict(version_info)
    if normalized.get('version') is None and normalized.get('download_count') is not None:
        normalized['version'] = normalized['download_count']

    return normalized


def is_legacy_download_count_version(version_info):
    """判断版本信息是否仍使用下载量作为版本号"""
    if not version_info:
        return False

    version = version_info.get('version')
    download_count = version_info.get('download_count')
    return version is not None and download_count is not None and version == download_count


def should_skip_update(latest_version_info, local_version_info):
    """判断是否应跳过更新"""
    if is_legacy_download_count_version(local_version_info) and not is_legacy_download_count_version(latest_version_info):
        return False

    latest_version = latest_version_info.get('version', 0)
    local_version = local_version_info.get('version', 0)
    return latest_version <= local_version


def build_version_info_for_save(latest_version_info):
    """构建保存到本地的版本信息"""
    return {
        'version': latest_version_info.get('version', 0),
        'download_count': latest_version_info.get('download_count', latest_version_info.get('version', 0)),
        'update_time': latest_version_info.get('update_time', ''),
        'word_count': latest_version_info.get('word_count', 0),
        'name': latest_version_info.get('name', ''),
    }


def load_version_info():
    """从文件加载版本信息"""
    if not os.path.exists(VERSION_INFO_PATH):
        return {'version': 0, 'update_time': '', 'word_count': 0}

    try:
        with open(VERSION_INFO_PATH, 'r', encoding='utf-8') as f:
            return normalize_version_info(json.load(f)) or {'version': 0, 'update_time': '', 'word_count': 0}
    except Exception as e:
        logger.error(f"加载版本信息失败: {e}")
        return {'version': 0, 'update_time': '', 'word_count': 0}


def save_version_info(version_info):
    """保存版本信息到文件"""
    version_info = build_version_info_for_save(version_info)
    try:
        with open(VERSION_INFO_PATH, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)
        logger.info(f"版本信息已保存: {version_info}")
    except Exception as e:
        logger.error(f"保存版本信息失败: {e}")


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
    """
    if offset >= 0:
        f.seek(offset)

    if length > 0:
        data = f.read(length)
        end = 0
        for i in range(0, len(data), 2):
            if i + 1 < len(data) and data[i] == 0 and data[i + 1] == 0:
                end = i
                break
        if end > 0:
            data = data[:end]
        return data.decode('utf-16le', errors='ignore')

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
            f.seek(0)
            header = f.read(4)
            if header != b'\x40\x15\x00\x00':
                logger.warning("文件头部不是搜狗细胞词库格式")

            f.seek(0x124)
            word_count = read_uint32(f)

            f.seek(0x130)
            name = read_utf16_str(f, -1, 64)

            f.seek(0x338)
            type_name = read_utf16_str(f, -1, 64)

            f.seek(0x540)
            description = read_utf16_str(f, -1, 1024)

            f.seek(0xd40)
            example = read_utf16_str(f, -1, 1024)

            info = {
                'word_count': word_count,
                'name': name,
                'type': type_name,
                'description': description,
                'example': example,
            }

            logger.debug(f"词库信息: {info}")
            return info
    except Exception as e:
        logger.error(f"获取词库信息失败: {e}", exc_info=True)
        return {'word_count': 0, 'name': '', 'type': '', 'description': '', 'example': ''}


def build_entry(word, pinyin, source='scel'):
    return {
        'word': word,
        'pinyin': pinyin.strip(),
        'source': source,
    }


def is_valid_word(word):
    return (
        bool(word)
        and 1 <= len(word) <= 10
        and all('\u4e00' <= c <= '\u9fff' or c.isdigit() or c in '，。：；？！（）【】《》""\'\'、' for c in word)
    )


def parse_scel_file(scel_path):
    """
    解析搜狗细胞词库文件，提取词条与原始拼音。

    这里沿用 SCEL 的经典解析布局，参考：
    https://github.com/studyzy/imewlconverter/blob/master/src/ImeWlConverterCore/IME/SougouPinyinScel.cs

    当前 Python 实现与参考实现对齐的部分：
    1. 先读取 0x1540 偏移处的拼音表，建立“拼音索引 -> 拼音字符串”的映射；
    2. 再按“同音词组”读取词条块；
    3. 每个词组先给出一串拼音索引，随后该组里的多个词共享这串拼音；
    4. 词记录中的附加字段继续跳过，只保留 word / pinyin 这两个当前链路真正需要的结果。

    与参考实现不追求逐行一致的部分：
    - 参考实现会保留更多中间字段（如 rank / unknown 字段），这里有意简化；
    - 参考实现对索引命中的判断更偏 C# 容器语义，这里改成 `idx in pinyin_dict`，更贴近 Python dict 的实际语义。
    """
    try:
        with open(scel_path, 'rb') as f:
            info = get_scel_info(scel_path)
            logger.info(f"词库名称: {info['name']}, 词条数: {info['word_count']}")

            # 拼音表从 0x1540 开始；这里先读一个 Int32。
            # 参考实现将其命名为 pyDicLen，但实际按“拼音表条目数”来循环读取。
            f.seek(0x1540)
            pinyin_count = read_uint32(f)
            logger.debug(f"拼音表中的拼音数量: {pinyin_count}")

            pinyin_dict = {}
            for _ in range(pinyin_count):
                pinyin_idx = read_uint16(f)
                # 第二个字段是后续拼音文本的字节长度，不包含前面的 4 字节头部。
                pinyin_len = read_uint16(f)
                pinyin_data = f.read(pinyin_len)
                try:
                    pinyin = pinyin_data.decode('utf-16le').strip().lower()
                    pinyin_dict[pinyin_idx] = pinyin
                except Exception:
                    logger.warning(f"解析拼音 {pinyin_idx} 失败")

            logger.debug(f"成功解析拼音表，共 {len(pinyin_dict)} 个拼音")

            entries = []
            count = 0

            try:
                while True:
                    # 每个词组头部 4 字节由两个 UInt16 组成：
                    # - same_pinyin_count: 同拼音词条数量
                    # - pinyin_index_len: 后续拼音索引区的字节数，而不是索引个数
                    same_pinyin_count = read_uint16(f)
                    pinyin_index_len = read_uint16(f)
                    if pinyin_index_len <= 0 or same_pinyin_count <= 0:
                        break

                    # 拼音索引区每 2 字节是一个索引，所以真实索引个数 = pinyin_index_len // 2。
                    pinyin_indices = []
                    for _ in range(pinyin_index_len // 2):
                        idx = read_uint16(f)
                        if idx in pinyin_dict:
                            pinyin_indices.append(pinyin_dict[idx])
                        else:
                            # 参考实现在这里也保留回退分支；当前 Python 实现按 dict membership 判断是否命中。
                            pinyin_indices.append(chr(idx - len(pinyin_dict) + 97))

                    joined_pinyin = ' '.join(part for part in pinyin_indices if part).strip()

                    for _ in range(same_pinyin_count):
                        # 词记录结构里，word_len 是 UTF-16LE 词文本的字节数；字符数通常约等于 word_len // 2。
                        # 词文本之后还有 12 字节附加字段：unknown1(Int16) + unknown2(Int32) + 6 字节尾部。
                        # 这些字段在当前链路里不参与产物生成，因此有意跳过，只保留词文本和该组原始拼音。
                        word_len = read_uint16(f)
                        word_data = f.read(word_len)
                        word = word_data.decode('utf-16le', errors='ignore')

                        _ = read_uint16(f)
                        _ = read_uint32(f)
                        _ = f.read(6)

                        if is_valid_word(word):
                            entries.append(build_entry(word, joined_pinyin, source='scel'))
                            count += 1
                            if count % 1000 == 0:
                                logger.debug(f"已解析 {count} 个词条")
            except Exception as e:
                # 文件尾部或局部格式异常时，已经成功提取的词条仍然可用，不在这里整体丢弃。
                logger.warning(f"解析词条过程中遇到错误: {e}")

            logger.info(f"成功解析词库，共找到 {len(entries)} 个词条")
            if not entries:
                logger.warning('未解析到任何词条')
                return []

            return entries
    except Exception as e:
        logger.error(f"解析词库文件失败: {e}", exc_info=True)
        return []


def extract_words(entries):
    """按出现顺序提取词条文本，并去重空词。"""
    words = []
    seen = set()
    for entry in entries:
        word = entry.get('word', '') if isinstance(entry, dict) else str(entry)
        if not word or word in seen:
            continue
        seen.add(word)
        words.append(word)
    return words


def build_pronunciation_map(entries):
    """从词条条目中提取稳定拼音映射，首次出现优先。"""
    mapping = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        word = entry.get('word', '')
        pinyin = entry.get('pinyin', '').strip()
        if word and pinyin and word not in mapping:
            mapping[word] = pinyin
    return mapping


def save_to_txt(words, file_path):
    """保存当前词条到 txt，保留输入顺序。"""
    ordered_words = extract_words(words)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for word in ordered_words:
                f.write(f"{word}\n")
        logger.info(f"词条已保存到: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存词条失败: {e}")
        return False


def save_words_to_txt(words, file_path):
    """保存词集合到 txt，按字典序稳定输出。"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for word in sorted(words):
                f.write(f"{word}\n")
        logger.info(f"词集合已保存到: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存词集合失败: {e}")
        return False


def save_pronunciations_to_tsv(pronunciations, file_path):
    """保存词到拼音的稳定映射。"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for word in sorted(pronunciations):
                pinyin = pronunciations[word].strip()
                if pinyin:
                    f.write(f"{word}\t{pinyin}\n")
        logger.info(f"拼音映射已保存到: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存拼音映射失败: {e}")
        return False


def load_pronunciations_from_tsv(file_path):
    """从 TSV 文件读取词到拼音的映射。"""
    if not os.path.exists(file_path):
        return {}

    try:
        pronunciations = {}
        with open(file_path, 'r', encoding='utf-8') as f:
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


def load_accumulated_words():
    """加载累积的词条集合。"""
    if not os.path.exists(ACCUMULATED_TXT_PATH):
        return set()

    try:
        with open(ACCUMULATED_TXT_PATH, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        logger.error(f"加载累积词条失败: {e}")
        return set()


def load_current_pronunciations():
    return load_pronunciations_from_tsv(CURRENT_PINYIN_PATH)


def load_accumulated_pronunciations():
    return load_pronunciations_from_tsv(ACCUMULATED_PINYIN_PATH)


def update_accumulated_data(current_entries):
    """更新累计词集合与累计拼音映射，新词补入、旧词冻结。"""
    accumulated_words = load_accumulated_words()
    accumulated_pronunciations = load_accumulated_pronunciations()

    old_count = len(accumulated_words)
    current_words = extract_words(current_entries)
    current_pronunciations = build_pronunciation_map(current_entries)

    for word in current_words:
        accumulated_words.add(word)
        if word not in accumulated_pronunciations and word in current_pronunciations:
            accumulated_pronunciations[word] = current_pronunciations[word]

    if not save_words_to_txt(accumulated_words, ACCUMULATED_TXT_PATH):
        return False

    if not save_pronunciations_to_tsv(accumulated_pronunciations, ACCUMULATED_PINYIN_PATH):
        return False

    new_count = len(accumulated_words)
    logger.info(f"累积词条已更新: 原有 {old_count} 个，现有 {new_count} 个，新增 {new_count - old_count} 个")
    return True


def update_accumulated_words(current_words):
    """兼容旧接口：仅更新累计词集合。"""
    entries = []
    for word in current_words:
        entries.append(build_entry(word, '', source='legacy'))
    return update_accumulated_data(entries)


def run_update(force_update=False):
    """执行词库更新并返回状态"""
    os.makedirs(DATA_DIR, exist_ok=True)

    latest_version_info = normalize_version_info(get_latest_version_info())
    local_version_info = load_version_info()

    if force_update:
        logger.info('强制更新模式')
        if not latest_version_info:
            latest_version_info = build_version_info_for_save(local_version_info)
            latest_version_info['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elif not latest_version_info:
        logger.error('无法获取有效的版本信息')
        return STATUS_ERROR
    elif should_skip_update(latest_version_info, local_version_info):
        logger.info(f"当前已是最新版本: {local_version_info.get('version', 0)}，无需更新")
        return STATUS_NO_UPDATE

    scel_path = download_scel_file()
    if not scel_path:
        logger.error('下载词库文件失败')
        return STATUS_ERROR

    entries = parse_scel_file(scel_path)
    if not entries:
        logger.error('解析词库文件失败或未找到词条，退出')
        return STATUS_ERROR

    if not save_to_txt(entries, CURRENT_TXT_PATH):
        return STATUS_ERROR

    current_pronunciations = build_pronunciation_map(entries)
    if not save_pronunciations_to_tsv(current_pronunciations, CURRENT_PINYIN_PATH):
        return STATUS_ERROR

    if not update_accumulated_data(entries):
        return STATUS_ERROR

    latest_version_info['word_count'] = len(extract_words(entries))
    save_version_info(latest_version_info)

    logger.info('词库更新完成')
    return STATUS_UPDATED


def main():
    """主函数"""
    force_update = len(sys.argv) > 1 and sys.argv[1] == '--force'
    status = run_update(force_update=force_update)
    print(f'STATUS:{status}')
    return status


if __name__ == '__main__':
    status = main()
    sys.exit(0 if status != STATUS_ERROR else 1)
