import os
import json

# 从环境变量读取 B 站认证
BILIBILI_AUTH_JSON = os.getenv("BILIBILI_AUTH", "{}")
try:
    _auth = json.loads(BILIBILI_AUTH_JSON)
except json.JSONDecodeError:
    _auth = {}

SESSDATA = _auth.get("sessdata", "")
BILI_JCT = _auth.get("bili_jct", "")
BUVID3 = _auth.get("buvid3", "")
DEDEUSERID = _auth.get("dedeuserid", "")

# 从环境变量读取 Cloudflare D1 配置
CF_D1_JSON = os.getenv("CF_D1", "{}")
try:
    _cf = json.loads(CF_D1_JSON)
except json.JSONDecodeError:
    _cf = {}

CF_ACCOUNT_ID = _cf.get("account_id", "")
CF_DATABASE_ID = _cf.get("database_id", "")
CF_API_TOKEN = _cf.get("api_token", "")
