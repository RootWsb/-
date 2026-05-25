"""
公共工具函数 — 从多个模块提取的重复代码，统一维护。

包含：
    - repair_mojibake: 修复 UTF-8 乱码
    - log_error: UTF-8 错误日志
    - call_deepseek_api: DeepSeek API 调用
    - parse_llm_response: LLM JSON 响应解析
    - load_jsonl / save_jsonl: JSONL 文件读写
    - normalize_api_base: API URL 规范化
    - sanitize_generated_item: 生成数据规范化
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests


# ============================================
# 文本修复
# ============================================

def repair_mojibake(text: str) -> str:
    """
    修复常见的 UTF-8 被 latin1/cp1252 错解码后的乱码。

    某些中转 API 偶尔返回如 "å¸®æˆ" 而不是 "帮我" 的乱码文本。
    修复失败时保留原始文本。
    """
    if not isinstance(text, str):
        return text
    suspicious = sum(text.count(ch) for ch in ("Ã", "Â", "å", "æ", "ç", "è", "é", "ï¼"))
    if suspicious < 2:
        return text
    for encoding in ("latin1", "cp1252"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
            if repaired and repaired != text:
                return repaired
        except UnicodeError:
            continue
    return text


# ============================================
# 日志
# ============================================

def log_error(log_path: Optional[Path], message: str):
    """写入 UTF-8 调试日志，避免 Windows 控制台编码问题影响排查。"""
    if not log_path:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(message.rstrip() + "\n")


# ============================================
# API 调用
# ============================================

def normalize_api_base(api_base: str) -> str:
    """接受 https://host 或 https://host/v1，返回干净的基础 URL。"""
    return api_base.rstrip("/")


def call_deepseek_api(
    prompt: str,
    api_key: str,
    model: str = "deepseek-v4-pro",
    api_base: str = "https://inferaichat.com/v1",
    system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    log_path: Optional[Path] = None,
) -> str:
    """
    调用 DeepSeek 兼容 API（支持中转站）。

    返回 assistant 的 content 字符串，失败时抛出异常。
    """
    api_base = normalize_api_base(api_base)
    url = f"{api_base}/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.encoding = "utf-8"
            if response.status_code >= 400:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:1000]}")
            result = response.json()
            message = result["choices"][0]["message"]
            # 优先取 content（最终答案），reasoning_content 是思考过程
            content = message.get("content") or ""
            if content:
                return repair_mojibake(content)
            reasoning = message.get("reasoning_content") or ""
            if reasoning:
                reasoning = repair_mojibake(reasoning)
                log_error(
                    log_path,
                    f"[API reasoning without final content] {reasoning[:1000]}",
                )
                # 中转站兼容：有些模型把 JSON 放在 reasoning_content 里
                if "{" in reasoning and "}" in reasoning:
                    return reasoning
            raise ValueError(f"API returned empty message content: {result}")
        except Exception as e:
            if attempt < 2:
                log_error(
                    log_path,
                    f"[API attempt {attempt+1}/3] {type(e).__name__}: {str(e)}",
                )
                time.sleep(2)
                continue
            log_error(
                log_path,
                f"[API final failure] {type(e).__name__}: {str(e)}",
            )
            raise

    return ""


# ============================================
# JSON 解析
# ============================================

def parse_llm_json(response: str) -> Dict:
    """
    解析 LLM 返回的 JSON 响应，处理各种格式问题。
    """
    if not response or not response.strip():
        raise ValueError("LLM 返回空响应")

    response = repair_mojibake(response.strip())

    # 去掉 Markdown 代码块
    if response.startswith("```"):
        lines = response.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        response = "\n".join(lines).strip()

    # 直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 提取 { ... } 块
    start = response.find("{")
    end = response.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_str = response[start : end + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # 正则匹配最外层 {}
    match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法解析 LLM 响应: {response[:1000]}")


def parse_llm_json_array(response: str) -> List[Dict]:
    """
    解析 LLM 返回的 JSON 数组响应，支持截断修复。
    比 parse_llm_json 更宽容：自动补全截断的 JSON。
    """
    if not response or not response.strip():
        return []

    response = repair_mojibake(response.strip())

    # 去掉 Markdown 代码块
    if response.startswith("```"):
        lines = response.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        response = "\n".join(lines).strip()

    # 1. 直接解析完整数组
    try:
        result = json.loads(response)
        return result if isinstance(result, list) else [result]
    except json.JSONDecodeError:
        pass

    # 2. 提取 [ ... ] 块并尝试修复截断
    start = response.find("[")
    end = response.rfind("]")
    if start != -1:
        json_str = response[start:]
        # 如果没有找到 ] 或 ] 在 [ 之前，说明数组被截断了
        if end == -1 or end < start:
            # 去掉末尾可能不完整的逗号
            json_str = json_str.rstrip().rstrip(",")
            json_str += "]"
        else:
            json_str = response[start : end + 1]

        try:
            result = json.loads(json_str)
            return result if isinstance(result, list) else [result]
        except json.JSONDecodeError:
            # 尝试逐个对象提取
            pass

    # 3. 正则逐个提取 { ... } 对象
    objects = []
    for match in re.finditer(r'\{[^{}]*"user_message"[^{}]*\}', response, re.DOTALL):
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict) and "user_message" in obj:
                objects.append(obj)
        except json.JSONDecodeError:
            continue

    return objects


def sanitize_generated_item(item: Dict) -> Dict:
    """规范化合成数据的字段，确保类型和内容一致。"""
    item = dict(item)
    if isinstance(item.get("user_message"), str):
        item["user_message"] = repair_mojibake(item["user_message"]).strip()
    if isinstance(item.get("reasoning"), str):
        item["reasoning"] = repair_mojibake(item["reasoning"]).strip()
    if not isinstance(item.get("ideal_skills"), list):
        item["ideal_skills"] = []
    item["ideal_skills"] = [
        str(skill).strip()
        for skill in item.get("ideal_skills", [])
        if str(skill).strip()
    ][:3]
    return item


# ============================================
# JSONL 文件读写
# ============================================

def load_jsonl(path: str) -> List[Dict]:
    """加载 JSONL 文件，跳过空行和解析失败的行。"""
    if not path or not os.path.exists(path):
        return []
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return data


def save_jsonl(data: List[Dict], path: str):
    """保存数据为 JSONL 格式。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
