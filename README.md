# 搜狗网络流行新词自动更新工具

这个项目用于自动从搜狗拼音输入法词库下载网络流行新词，并将其转换为纯文本格式和Rime输入法可用的YAML格式。

备注：本项目在 2026 年 4 月使用 vibe coding 持续迭代。

## 功能特点

- 自动从搜狗拼音输入法词库下载最新的网络流行新词
- 将搜狗细胞词库格式(.scel)转换为纯文本格式(.txt)
- 生成两个版本的词库：当前版本和累积版本（包含历史词条）
- 保留 SCEL 原拼音映射，避免累计词库历史词被重复重算
- 将词库转换为Rime输入法可用的YAML格式
- 通过GitHub Actions实现每日自动更新

## 文件结构

```
.
├── .github/workflows/   # GitHub Actions工作流配置
│   └── update_dict.yml  # 自动更新词库的工作流
├── data/                # 存放词库数据
│   ├── sogou_network_words_current.txt        # 当前版本词集合真值（纯文本）
│   ├── sogou_network_words_accumulated.txt    # 累积词集合真值（纯文本）
│   ├── sogou_network_words_current_pinyin.tsv # 当前版本拼音映射（SCEL 原拼音优先）
│   ├── sogou_network_words_accumulated_pinyin.tsv # 累积版本稳定拼音映射（历史词冻结）
│   ├── luna_pinyin.sogoupopular.current.dict.yaml  # 当前版本词库（Rime格式）
│   ├── luna_pinyin.sogoupopular.dict.yaml     # 累积版本词库（Rime格式）
│   └── version_info.json  # 版本信息
├── scripts/             # 脚本文件
│   ├── download_and_convert.py  # 下载并解析 SCEL，写出 txt/tsv 真值
│   ├── convert_to_rime.py       # 从 txt + tsv 生成 Rime YAML
│   ├── repair_pronunciation_data.py  # 一次性修复当前仓库拼音数据
│   └── run_all.py               # 运行所有流程
├── requirements.txt     # 依赖包列表
└── README.md            # 项目说明
```

## SCEL 解析参考

当前 `scripts/download_and_convert.py` 中的 `parse_scel_file()` 参考自：
- `ImeWlConverter / SougouPinyinScel.cs`
- https://github.com/studyzy/imewlconverter/blob/master/src/ImeWlConverterCore/IME/SougouPinyinScel.cs

当前实现与参考实现对齐的核心点：
- 拼音表从 `0x1540` 开始读取；
- 词组头部由 `same_pinyin_count(UInt16)` 和 `pinyin_index_len(UInt16)` 组成；
- `pinyin_index_len` 表示字节数，真实索引个数为 `pinyin_index_len / 2`；
- 词记录中的 `word_len` 是 UTF-16LE 文本字节数；
- 词文本后的附加字段当前有意跳过，只保留 `word` 和 `pinyin`。

当前实现与参考实现不追求逐行一致：
- Python 版本有意简化，只保留当前链路需要的 `word / pinyin`；
- 索引命中判断使用 `idx in pinyin_dict`，以贴合 Python `dict` 语义。

## 使用方法

### 本地运行

1. 克隆仓库：

```bash
git clone https://github.com/ASC8384/SogouPopularDict.git
cd SogouPopularDict
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 运行完整流程：

```bash
python scripts/run_all.py
```

或者分步运行：

```bash
# 下载并解析 SCEL，写出词集合与拼音映射
python scripts/download_and_convert.py

# 从 txt + tsv 转换为Rime格式
python scripts/convert_to_rime.py

# 一次性修复当前仓库里的 sidecar / YAML 数据
# --version 使用 data/version_info.json 中 update_time 对应的 YYYY.MM.DD
python scripts/repair_pronunciation_data.py --version 2026.04.13
```

### 在Rime输入法中使用

1. 将生成的YAML文件复制到Rime的用户目录：
   - Windows: `%APPDATA%\Rime`
   - macOS: `~/Library/Rime`
   - Linux: `~/.config/ibus/rime` 或 `~/.config/fcitx/rime`

2. 在Rime的配置文件中添加词库，例如在`default.custom.yaml`中：

```yaml
patch:
  schema_list:
    - schema: luna_pinyin
  luna_pinyin:
    dictionary: luna_pinyin
    custom_dict:
      - luna_pinyin.sogoupopular
```

3. 重新部署Rime输入法。

### 自动更新

本项目使用GitHub Actions实现每日自动检查和更新。工作流程如下：

1. 每天自动检查搜狗词库是否有更新
2. 如有更新，下载并转换词库
3. 自动提交更改到仓库

您可以通过以下方式手动触发更新：

1. 在GitHub仓库页面，点击"Actions"标签
2. 选择"自动更新搜狗网络流行新词词库"工作流
3. 点击"Run workflow"按钮

## 许可证

MIT

## 致谢

- 感谢搜狗拼音输入法提供的网络流行新词词库
- 感谢Rime输入法开发团队 