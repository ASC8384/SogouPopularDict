# 搜狗网络流行新词自动更新工具

这个项目用于自动从搜狗拼音输入法词库下载网络流行新词，并将其转换为纯文本格式和Rime输入法可用的YAML格式。

## 功能特点

- 自动从搜狗拼音输入法词库下载最新的网络流行新词
- 将搜狗细胞词库格式(.scel)转换为纯文本格式(.txt)
- 生成两个版本的词库：当前版本和累积版本（包含历史词条）
- 将词库转换为Rime输入法可用的YAML格式
- 通过GitHub Actions实现每日自动更新

## 文件结构

```
.
├── .github/workflows/   # GitHub Actions工作流配置
│   └── update_dict.yml  # 自动更新词库的工作流
├── data/                # 存放词库数据
│   ├── sogou_network_words_current.txt        # 当前版本词库（纯文本）
│   ├── sogou_network_words_accumulated.txt    # 累积版本词库（纯文本）
│   ├── luna_pinyin.sogoupopular.current.dict.yaml  # 当前版本词库（Rime格式）
│   ├── luna_pinyin.sogoupopular.dict.yaml     # 累积版本词库（Rime格式）
│   └── version_info.json  # 版本信息
├── scripts/             # 脚本文件
│   ├── download_and_convert.py  # 下载并转换搜狗词库
│   ├── convert_to_rime.py       # 转换为Rime格式
│   └── run_all.py               # 运行所有流程
├── requirements.txt     # 依赖包列表
└── README.md            # 项目说明
```

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
# 下载并转换词库
python scripts/download_and_convert.py

# 转换为Rime格式
python scripts/convert_to_rime.py
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