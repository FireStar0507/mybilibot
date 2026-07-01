# record.py
import httpx
import json
from datetime import datetime
from bilibili_api import user
from config import CF_ACCOUNT_ID, CF_DATABASE_ID, CF_API_TOKEN
from tools import log_info, log_success, log_error, credential   # 从 tools 导入 credential

# ---------- 使用 tools 的 credential 获取用户信息 ----------
async def get_user_info():
    """获取当前登录用户信息，返回完整字典"""
    try:
        info = await user.get_self_info(credential=credential)
        return info
    except Exception as e:
        log_error(f"获取用户信息失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return None

# ---------- Cloudflare D1 客户端 ----------
class D1Client:
    def __init__(self, account_id, database_id, api_token):
        self.account_id = account_id
        self.database_id = database_id
        self.api_token = api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"

    async def execute(self, sql: str):
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            payload = {"sql": sql}
            resp = await client.post(self.base_url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def create_table_if_not_exists(self):
        sql = """
        CREATE TABLE IF NOT EXISTS user_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_time TEXT NOT NULL,
            mid TEXT NOT NULL,
            name TEXT,
            level INTEGER,
            coins REAL,
            exp INTEGER,
            following INTEGER,
            follower INTEGER,
            extra_json TEXT
        )
        """
        await self.execute(sql)
        log_success("D1 表已就绪")

    async def insert_record(self, data: dict):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        mid = data.get('mid', '')
        name = data.get('name', '')
        level = data.get('level', 0)
        coins = data.get('coins', 0.0)
        exp = data.get('current_exp', 0)
        following = data.get('following', 0)
        follower = data.get('follower', 0)
        extra_json = json.dumps(data, ensure_ascii=False)

        def sqlescape(val):
            if val is None:
                return "NULL"
            if isinstance(val, (int, float)):
                return str(val)
            return "'" + str(val).replace("'", "''") + "'"

        sql = f"""
        INSERT INTO user_records (
            record_time, mid, name, level, coins, exp, following, follower, extra_json
        ) VALUES (
            {sqlescape(now)},
            {sqlescape(mid)},
            {sqlescape(name)},
            {level},
            {coins},
            {exp},
            {following},
            {follower},
            {sqlescape(extra_json)}
        )
        """
        await self.execute(sql)
        log_success("数据已写入 D1")

# ---------- 对外接口 ----------
async def save_user_record():
    log_info("开始记录用户数据到 D1...")

    if not all([CF_ACCOUNT_ID, CF_DATABASE_ID, CF_API_TOKEN]):
        log_error("D1 配置不完整，请检查 config.py")
        return

    info = await get_user_info()
    if not info:
        log_error("获取用户信息失败，跳过记录")
        return

    # 提取表字段所需数据（可自由扩展）
    data = {
        'mid': info.get('mid'),
        'name': info.get('name'),
        'level': info.get('level'),
        'coins': info.get('coins'),
        'current_exp': info.get('level_exp', {}).get('current_exp'),
        'following': info.get('following'),
        'follower': info.get('follower'),
        'raw': info   # 完整 JSON 存 extra_json
    }

    client = D1Client(CF_ACCOUNT_ID, CF_DATABASE_ID, CF_API_TOKEN)
    try:
        await client.create_table_if_not_exists()
        await client.insert_record(data)
        log_success("用户记录已保存到 D1")
    except Exception as e:
        log_error(f"D1 操作失败: {e}")
        import traceback
        traceback.print_exc()
