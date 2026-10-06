import os
import json

def parse_cookie_string(cookie_str: str) -> dict:
    """
    从浏览器复制的完整 Cookie 字符串中提取所需字段。
    输入示例：
        "CURRENT_QUALITY=0;b_lsid=xxx;buvid3=xxx;SESSDATA=xxx;bili_jct=xxx;DedeUserID=xxx;..."
    返回：
        {"sessdata": "...", "bili_jct": "...", "buvid3": "...", "dedeuserid": "..."}
    """
    result = {
        "sessdata": "",
        "bili_jct": "",
        "buvid3": "",
        "dedeuserid": "",
    }
    if not cookie_str:
        return result

    # 按分号拆分，每项形如 key=value
    for item in cookie_str.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, _, value = item.partition("=")
        key = key.strip()
        value = value.strip()

        key_lower = key.lower()
        if key_lower == "sessdata":
            result["sessdata"] = value
        elif key_lower == "bili_jct":
            result["bili_jct"] = value
        elif key_lower == "buvid3":
            result["buvid3"] = value
        elif key_lower == "dedeuserid":
            result["dedeuserid"] = value

    return result


def load_bilibili_auth() -> dict:
    """
    读取 BILIBILI_AUTH 环境变量，支持两种格式：
    1. JSON: {"sessdata":"...", "bili_jct":"...", "buvid3":"...", "dedeuserid":"..."}
    2. 完整 Cookie 字符串: "SESSDATA=xxx;bili_jct=xxx;buvid3=xxx;DedeUserID=xxx;..."
    自动判断格式并解析。
    """
    raw = os.getenv("BILIBILI_AUTH", "").strip()
    if not raw:
        return {"sessdata": "", "bili_jct": "", "buvid3": "", "dedeuserid": ""}

    # 尝试 JSON 解析
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            return {
                "sessdata": data.get("sessdata", ""),
                "bili_jct": data.get("bili_jct", ""),
                "buvid3": data.get("buvid3", ""),
                "dedeuserid": data.get("dedeuserid", ""),
            }
        except json.JSONDecodeError:
            pass  # 解析失败，回退到 Cookie 字符串解析

    # 当作完整 Cookie 字符串解析
    return parse_cookie_string(raw)


# ---------- 加载 B 站认证 ----------
_auth = load_bilibili_auth()
SESSDATA = _auth["sessdata"]
BILI_JCT = _auth["bili_jct"]
BUVID3 = _auth["buvid3"]
DEDEUSERID = _auth["dedeuserid"]


# ---------- 加载 Cloudflare D1 配置 ----------
def load_cf_d1() -> dict:
    """
    读取 CF_D1 环境变量，支持：
    1. JSON: {"account_id":"...", "database_id":"...", "api_token":"..."}
    2. 纯 api_token 字符串（方便快速替换）
    """
    raw = os.getenv("CF_D1", "").strip()
    if not raw:
        return {"account_id": "", "database_id": "", "api_token": ""}

    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            return {
                "account_id": data.get("account_id", ""),
                "database_id": data.get("database_id", ""),
                "api_token": data.get("api_token", ""),
            }
        except json.JSONDecodeError:
            pass

    # 如果不是 JSON，可能是仅 api_token（此时 account_id/database_id 需另外提供）
    # 这里兜底返回空
    return {"account_id": "", "database_id": "", "api_token": raw}


_cf = load_cf_d1()
CF_ACCOUNT_ID = _cf["account_id"]
CF_DATABASE_ID = _cf["database_id"]
CF_API_TOKEN = _cf["api_token"]
