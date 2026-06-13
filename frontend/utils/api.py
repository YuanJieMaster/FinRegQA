"""
API 客户端模块
API Client Module
"""

import requests
from typing import Optional, Dict, Any
from config import (
    REQUEST_TIMEOUT_ANSWER,
    REQUEST_TIMEOUT_INGEST,
    REQUEST_TIMEOUT_STATS,
)


class APIClient:
    """API 客户端封装"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.access_token: Optional[str] = None
    
    def set_access_token(self, token: str):
        """设置访问令牌"""
        self.access_token = token
    
    def clear_access_token(self):
        """清除访问令牌"""
        self.access_token = None
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    def _make_url(self, endpoint: str) -> str:
        """构建完整 URL"""
        return f"{self.base_url}/api/v1{endpoint}"
    
    def get(self, endpoint: str, params: Dict = None, timeout: int = None) -> Optional[requests.Response]:
        """发送 GET 请求"""
        url = self._make_url(endpoint)
        try:
            return requests.get(url, headers=self._get_headers(), params=params, timeout=timeout or REQUEST_TIMEOUT_STATS)
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.Timeout:
            return None
    
    def post(self, endpoint: str, data: Dict = None, json: Dict = None, files: Dict = None, timeout: int = None) -> Optional[requests.Response]:
        """发送 POST 请求"""
        url = self._make_url(endpoint)
        headers = self._get_headers()
        
        # 如果是文件上传，不需要设置 Content-Type
        if files:
            headers.pop("Content-Type", None)
        
        try:
            if files:
                return requests.post(url, headers=headers, data=data, files=files, timeout=timeout or REQUEST_TIMEOUT_INGEST)
            elif json:
                return requests.post(url, headers=headers, json=json, timeout=timeout or REQUEST_TIMEOUT_ANSWER)
            else:
                return requests.post(url, headers=headers, data=data, timeout=timeout or REQUEST_TIMEOUT_ANSWER)
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.Timeout:
            return None
    
    def put(self, endpoint: str, json: Dict = None, timeout: int = None) -> Optional[requests.Response]:
        """发送 PUT 请求"""
        url = self._make_url(endpoint)
        try:
            return requests.put(url, headers=self._get_headers(), json=json, timeout=timeout or REQUEST_TIMEOUT_ANSWER)
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.Timeout:
            return None
    
    def delete(self, endpoint: str, timeout: int = None) -> Optional[requests.Response]:
        """发送 DELETE 请求"""
        url = self._make_url(endpoint)
        try:
            return requests.delete(url, headers=self._get_headers(), timeout=timeout or REQUEST_TIMEOUT_STATS)
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.Timeout:
            return None


# 全局 API 客户端实例
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """获取全局 API 客户端实例"""
    global _api_client
    if _api_client is None:
        from utils.session import get_api_url
        _api_client = APIClient(base_url=get_api_url())
    return _api_client


def reset_api_client():
    """重置全局 API 客户端"""
    global _api_client
    _api_client = None


# =============================================================================
# 认证相关 API
# =============================================================================

def api_login(username: str, password: str, api_url: str = None) -> Dict[str, Any]:
    """用户登录"""
    client = APIClient(base_url=api_url) if api_url else get_api_client()
    try:
        response = requests.post(
            f"{client.base_url}/api/v1/auth/login",
            data={"username": username, "password": password},
            timeout=30
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_register(username: str, email: str, password: str, confirm_password: str, api_url: str = None) -> Dict[str, Any]:
    """用户注册"""
    client = APIClient(base_url=api_url) if api_url else get_api_client()
    try:
        response = requests.post(
            f"{client.base_url}/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "confirm_password": confirm_password
            },
            timeout=30
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_request_password_reset(email: str, api_url: str = None) -> Dict[str, Any]:
    """请求密码重置"""
    client = APIClient(base_url=api_url) if api_url else get_api_client()
    try:
        response = requests.post(
            f"{client.base_url}/api/v1/auth/password/reset-request",
            json={"email": email},
            timeout=30
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# 知识库相关 API
# =============================================================================

def api_get_answer(question: str, region: str = None, mode: str = "hybrid", api_url: str = None) -> Dict[str, Any]:
    """获取问答答案"""
    try:
        response = requests.post(
            f"{api_url or get_api_url()}/api/knowledge/answer",
            json={
                "question": question,
                "region": region,
                "mode": mode,
            },
            timeout=REQUEST_TIMEOUT_ANSWER,
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_get_answer_stream(question: str, region: str = None, mode: str = "hybrid", api_url: str = None):
    """流式获取问答答案 (SSE 生成器)

    逐 event 产出 dict: {"event": str, "data": str}
    event 取值: "meta" | "answer" | "done"
    """
    import json as _json
    try:
        response = requests.post(
            f"{api_url or get_api_url()}/api/knowledge/answer/stream",
            json={
                "question": question,
                "region": region,
                "mode": mode,
            },
            stream=True,
            timeout=REQUEST_TIMEOUT_ANSWER,
        )
        if response.status_code != 200:
            yield {"event": "error", "data": f"HTTP {response.status_code}"}
            return

        current_event = None
        current_data = None
        for line in response.iter_lines(decode_unicode=True):
            if line is None:
                continue
            if line.startswith("event: "):
                current_event = line[7:]
            elif line.startswith("data: "):
                current_data = line[6:]
            elif line == "":
                # 空行表示一个事件结束
                if current_event and current_data is not None:
                    if current_event == "meta":
                        try:
                            parsed = _json.loads(current_data)
                        except Exception:
                            parsed = current_data
                        yield {"event": "meta", "data": parsed}
                    elif current_event in ("answer", "reasoning"):
                        yield {"event": current_event, "data": current_data}
                    elif current_event == "done":
                        yield {"event": "done", "data": None}
                current_event = None
                current_data = None
    except Exception as e:
        yield {"event": "error", "data": str(e)}


def api_ingest_document(file, category: str, regulation_type: str, region: str = None, source: str = None, min_chunk_size: int = 1, keep_separator: bool = True, batch_size: int = 100, api_url: str = None) -> Dict[str, Any]:
    """导入文档"""
    try:
        files = {"file": (file.name, file.getbuffer())}
        data = {
            "category": category,
            "regulation_type": regulation_type,
            "region": region,
            "source": source,
            "min_chunk_size": min_chunk_size,
            "keep_separator": keep_separator,
            "batch_size": batch_size,
        }
        response = requests.post(
            f"{api_url or get_api_url()}/api/knowledge/ingest",
            files=files,
            data=data,
            timeout=REQUEST_TIMEOUT_INGEST,
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_ingest_documents_batch(files: list, category: str, regulation_type: str, region: str = None, source: str = None, min_chunk_size: int = 1, keep_separator: bool = True, batch_size: int = 100, api_url: str = None) -> Dict[str, Any]:
    """批量导入文档"""
    try:
        # 构建文件列表
        file_list = []
        for file in files:
            file_list.append(
                ("files", (file.name, file.getbuffer()))
            )
        
        data = {
            "category": category,
            "regulation_type": regulation_type,
            "region": region,
            "source": source,
            "min_chunk_size": min_chunk_size,
            "keep_separator": keep_separator,
            "batch_size": batch_size,
        }
        
        response = requests.post(
            f"{api_url or get_api_url()}/api/knowledge/ingest/batch",
            files=file_list,
            data=data,
            timeout=max(REQUEST_TIMEOUT_INGEST * len(files), 300),  # 根据文件数量增加超时时间
        )
        
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_get_stats(api_url: str = None) -> Dict[str, Any]:
    """获取统计信息"""
    try:
        response = requests.get(
            f"{api_url or get_api_url()}/api/knowledge/stats",
            timeout=REQUEST_TIMEOUT_STATS
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_list_knowledge(page: int = 1, page_size: int = 20, category: str = None, region: str = None, search: str = None, api_url: str = None) -> Dict[str, Any]:
    """获取知识列表"""
    try:
        params = {"page": page, "page_size": page_size}
        if category:
            params["category"] = category
        if region:
            params["region"] = region
        if search:
            params["search"] = search
        
        response = requests.get(
            f"{api_url or get_api_url()}/api/knowledge/list",
            params=params,
            timeout=REQUEST_TIMEOUT_STATS
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_list_documents(api_url: str = None) -> Dict[str, Any]:
    """获取文档列表"""
    try:
        response = requests.get(
            f"{api_url or get_api_url()}/api/knowledge/documents",
            timeout=REQUEST_TIMEOUT_STATS
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_update_knowledge(kb_id: int, data: Dict, api_url: str = None) -> Dict[str, Any]:
    """更新知识点"""
    try:
        response = requests.put(
            f"{api_url or get_api_url()}/api/knowledge/update/{kb_id}",
            json=data,
            timeout=30
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_delete_knowledge(kb_id: int, api_url: str = None) -> Dict[str, Any]:
    """删除知识点"""
    try:
        response = requests.delete(
            f"{api_url or get_api_url()}/api/knowledge/delete/{kb_id}",
            timeout=30
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_delete_document(doc_id: int, api_url: str = None) -> Dict[str, Any]:
    """删除文档"""
    try:
        response = requests.delete(
            f"{api_url or get_api_url()}/api/knowledge/documents/{doc_id}",
            timeout=30
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# 评估相关 API
# =============================================================================

def api_evaluate_qa_batch(api_url: str, use_default: bool = True) -> Dict[str, Any]:
    """批量问答评估"""
    try:
        response = requests.post(
            f"{api_url}/api/evaluation/evaluate/batch",
            json={"api_url": api_url, "use_default_pairs": use_default},
            timeout=600
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail", "评估失败") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_evaluate_custom_question(question: str, api_url: str, ground_truth: str = None, keywords: list = None) -> Dict[str, Any]:
    """评估自定义问题"""
    try:
        payload = {
            "question": question,
            "ground_truth_answer": ground_truth,
            "expected_keywords": keywords
        }
        response = requests.post(
            f"{api_url}/api/evaluation/evaluate/custom/question",
            params={"api_url": api_url},
            json=payload,
            timeout=180
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("error", "测试失败") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_evaluate_ingest(api_url: str) -> Dict[str, Any]:
    """文档导入评估"""
    try:
        response = requests.post(
            f"{api_url}/api/evaluation/evaluate/ingest",
            json={"api_url": api_url},
            timeout=600
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("detail", "评估失败") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_evaluate_custom_file(file, api_url: str, category: str, regulation_type: str, region: str = None) -> Dict[str, Any]:
    """评估自定义文件"""
    try:
        files = {"file": (file.name, file.getvalue())}
        data = {
            "category": category,
            "regulation_type": regulation_type,
            "region": region,
            "min_chunk_size": 50,
            "max_chunk_size": 800
        }
        response = requests.post(
            f"{api_url}/api/evaluation/evaluate/custom/file",
            files=files,
            data=data,
            timeout=300
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": response.json().get("error", "测试失败") if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_get_qa_pairs(api_url: str) -> Dict[str, Any]:
    """获取问答对列表"""
    try:
        response = requests.get(
            f"{api_url}/api/evaluation/qa-pairs",
            timeout=30
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": "获取失败" if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_get_ingest_cases(api_url: str) -> Dict[str, Any]:
    """获取导入测试用例"""
    try:
        response = requests.get(
            f"{api_url}/api/evaluation/evaluate/ingest/cases",
            timeout=30
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": "获取失败" if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_get_reports(api_url: str) -> Dict[str, Any]:
    """获取历史报告"""
    try:
        response = requests.get(
            f"{api_url}/api/evaluation/reports",
            timeout=30
        )
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None, "error": "获取失败" if response.status_code != 200 else None}
    except Exception as e:
        return {"success": False, "error": str(e)}
