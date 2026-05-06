"""
前端配置文件
Frontend Configuration Module
"""

# HTTP 请求超时（秒）
REQUEST_TIMEOUT_ANSWER = 180
REQUEST_TIMEOUT_INGEST = 600
REQUEST_TIMEOUT_STATS = 120

# 地区选项
REGION_OPTIONS = [
    "全国",
    "浙江省",
    "江苏省",
    "上海市",
    "北京市",
    "广东省",
    "其他（自定义）",
]

# 文档分类选项
CATEGORY_OPTIONS = [
    "风险管理",
    "资本管理",
    "流动性管理",
    "内部控制",
    "信息披露",
    "其他"
]

# 搜索模式选项
SEARCH_MODE_OPTIONS = [
    {"value": "hybrid", "label": "混合搜索 (Hybrid)", "description": "结合语义向量和关键词搜索"},
    {"value": "vector", "label": "向量搜索 (Vector)", "description": "基于语义相似度搜索"},
    {"value": "keyword", "label": "关键词搜索 (Keyword)", "description": "基于关键词匹配搜索"},
]

# 默认 API 地址
DEFAULT_API_URL = "http://localhost:8000"

# 支持的文件类型
SUPPORTED_FILE_TYPES = [
    "pdf", "docx", "doc", "txt",
    "png", "jpg", "jpeg", "bmp", "tiff", "gif", "webp"
]

# 知识库管理每页条数选项
PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

# 评估难度选项
DIFFICULTY_OPTIONS = ["简单", "中等", "困难"]

# 评估类型
EVALUATION_TYPES = {
    "qa": "💬 问答准确率评估",
    "ingest": "📄 文档导入准确率评估"
}
