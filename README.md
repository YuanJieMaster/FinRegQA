# 金融制度文本分块器

基于LangChain的金融监管文档智能分块工具，专为金融制度文本的层级结构设计。

## 功能特性

### 1. 多格式文档加载
- **PDF**: 使用PyMuPDF提取，保留文本结构
- **DOCX**: 使用python-docx提取，保留段落格式  
- **TXT**: 直接读取纯文本文件

### 2. 智能分块策略
- 按金融监管文件的层级结构分割：**章 > 条 > 款 > 项**
- 保持法规条文的完整性，避免语义割裂
- 过滤小于200字的片段，确保知识点有效性
- 递归分割过大片段，优化检索效率

### 3. 文本清洗
- 去除水印（"内部资料"、"机密"等）
- 去除页眉页脚（页码、日期等）
- 规范化空白字符
- 去除PDF提取异常字符

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试

```bash
python api.py
streamlit run frontend.py
```

### 基本使用

```python
from financial_text_splitter import (
    FinancialRegulationSplitter,
    load_financial_document
)

# 1. 加载文档
document = load_financial_document("your_file.pdf", clean_text=True)

# 2. 初始化分块器
splitter = FinancialRegulationSplitter(
    min_chunk_size=200,  # 最小分块大小
    keep_separator=True  # 保留章节标识符
)

# 3. 分块
chunks = splitter.split_text(document.page_content)

print(f"知识点数量: {len(chunks)}")
```

## 核心组件

### FinancialRegulationSplitter
自定义文本分块器，继承自LangChain的TextSplitter。

**参数:**
- `separators`: 分隔符列表（默认：章/条/款/项/句号/分号）
- `min_chunk_size`: 最小分块大小，默认200字符
- `keep_separator`: 是否保留分隔符，默认True

### load_financial_document
文档加载函数，支持多种格式。

**参数:**
- `file_path`: 文件路径
- `clean_text`: 是否清洗文本，默认True

**返回:** LangChain Document对象

### clean_financial_text
文本清洗函数，去除水印和页眉页脚。

## 金融场景适配说明

### 为什么需要自定义分块器？

1. **结构化特征**: 金融监管文件采用"章-条-款-项"的严格层级结构，通用分块器无法识别
2. **语义完整性**: 法规条文需要保持完整，避免在检索时出现语义割裂
3. **长度控制**: 金融条文长度差异大，需要智能过滤和递归分割
4. **噪音过滤**: PDF提取的文本包含大量水印、页码等噪音，影响检索质量

### 分块策略优先级

```
第X章（章节）> 第X条（条款）> 第X款（款项）> (X)（项）> 。（句号）> ；（分号）
```

优先使用高层级分隔符，确保保留文档的逻辑结构。

## 测试输出示例

```
📊 分块统计:
  - 知识点总数: 15 个
  - 平均长度: 456 字符
  - 最短片段: 203 字符
  - 最长片段: 892 字符

📈 长度分布:
  - 200-500字: 8 个 (53.3%)
  - 500-1000字: 6 个 (40.0%)
  - 1000-2000字: 1 个 (6.7%)

🏗️ 文档结构分析:
  - 检测到章节: 5 个
  - 检测到条款: 13 个
```

## 后续扩展

可基于此分块器构建完整的金融监管问答系统：

1. **向量化**: 使用embedding模型将chunks转为向量
2. **向量存储**: 存入ChromaDB/Faiss等向量数据库
3. **检索增强**: 实现RAG（Retrieval-Augmented Generation）
4. **问答系统**: 结合LLM实现智能问答

## 依赖说明

- `langchain`: LangChain核心库
- `PyMuPDF`: PDF文本提取
- `python-docx`: DOCX文档处理
- `regex`: 正则表达式增强

## 许可证

MIT License
