"""
评测集加载工具
Evaluation Set Loader Utility

用于加载金融监管评测集 (xlsx) 并支持人工评测结果的本地持久化。
Loads the financial regulation evaluation set (xlsx) and supports local
persistence of human evaluation results.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# 尝试导入 openpyxl 与 pandas（启动时给出友好提示）
try:
    import openpyxl  # noqa: F401
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# 评测集 Excel 路径（项目根目录）
EVAL_XLSX_PATH = Path(__file__).resolve().parents[2] / "金融监管评测集.xlsx"

# 人工评测结果本地缓存路径
EVAL_RESULTS_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "human_eval_results.json"


# 评测选项（与 Excel 中 人工评测 列保持一致的可选值）
EVAL_OPTIONS = ["是", "否", "部分正确", "无法判断"]


def ensure_openpyxl() -> None:
    """确保 openpyxl 可用；不可用时给出明确指引。"""
    if not HAS_OPENPYXL:
        raise ImportError(
            "缺少依赖 openpyxl，无法读取 .xlsx 评测集。"
            "请执行：pip install openpyxl>=3.1.0"
        )


def _normalize_columns(df) -> List[str]:
    """规整列名：去空白 + 兼容全角空格。"""
    return [str(c).strip().replace("\u3000", "") for c in df.columns]


def load_evaluation_set(xlsx_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """加载评测集为字典列表。

    返回每条记录的字段：
        - id          : 行号（从 1 开始）
        - question    : 题目
        - ground_truth: 答案/标准答案
        - ai_answer   : AI 问答答案
        - human_eval  : 人工评测（来自原表，已与本地缓存合并）
    """
    ensure_openpyxl()

    path = Path(xlsx_path) if xlsx_path else EVAL_XLSX_PATH
    if not path.exists():
        raise FileNotFoundError(f"未找到评测集文件: {path}")

    if not HAS_PANDAS:
        # openpyxl 后备
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            wb.close()
            return []
        header = [str(c).strip().replace("\u3000", "") if c is not None else "" for c in rows[0]]
        records = []
        for idx, row in enumerate(rows[1:], start=1):
            item = {"id": idx}
            for col_name, value in zip(header, row):
                item[col_name] = "" if value is None else str(value)
            records.append(item)
        wb.close()
        items = records
    else:
        df = pd.read_excel(path)
        df.columns = _normalize_columns(df)
        items = []
        for idx, row in df.iterrows():
            items.append({
                "id": idx + 1,
                "question": str(row.get("问题", "") or "").strip(),
                "ground_truth": str(row.get("答案", "") or "").strip(),
                "ai_answer": str(row.get("AI问答答案", "") or "").strip(),
                "human_eval": _clean_cell(row.get("人工评测", "")),
            })

    # 合并本地持久化的人工评测结果
    cached = load_cached_results()
    for item in items:
        cached_value = cached.get(str(item["id"]))
        if cached_value and not item["human_eval"]:
            item["human_eval"] = cached_value
    return items


def _clean_cell(value: Any) -> str:
    """清洗单元格值：处理 NaN/None/浮点 1.0。"""
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        if value.is_integer():
            return str(int(value))
        return str(value)
    text = str(value).strip()
    if text.lower() in ("nan", "none", "null"):
        return ""
    return text


def load_cached_results() -> Dict[str, str]:
    """从本地 JSON 加载已保存的人工评测结果。"""
    if not EVAL_RESULTS_CACHE_PATH.exists():
        return {}
    try:
        with open(EVAL_RESULTS_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        return {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_cached_results(results: Dict[str, str]) -> None:
    """将人工评测结果保存到本地 JSON。"""
    EVAL_RESULTS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EVAL_RESULTS_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def clear_cached_results() -> None:
    """清空本地缓存。"""
    if EVAL_RESULTS_CACHE_PATH.exists():
        EVAL_RESULTS_CACHE_PATH.unlink()


def get_evaluation_summary(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """统计评测分布。"""
    summary: Dict[str, int] = {opt: 0 for opt in EVAL_OPTIONS}
    summary["未评测"] = 0
    for item in items:
        value = (item.get("human_eval") or "").strip()
        if not value:
            summary["未评测"] += 1
        elif value in summary:
            summary[value] += 1
        else:
            summary.setdefault(value, 0)
            summary[value] += 1
    return summary
