# record.py
import httpx
import json
from datetime import datetime, timezone, timedelta
from bilibili_api import user
from config import CF_ACCOUNT_ID, CF_DATABASE_ID, CF_API_TOKEN
from tools import log_info, log_success, log_error, credential

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
        """执行 SQL（不返回结果）"""
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            payload = {"sql": sql}
            resp = await client.post(self.base_url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def query(self, sql: str):
        """执行查询并返回结果行列表"""
        resp = await self.execute(sql)
        results = resp.get('result', [])
        if results:
            rows = results[0].get('results', [])
            return rows
        return []

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

    async def has_record_today(self):
        """检查今天（UTC+8）是否已有记录"""
        tz = timezone(timedelta(hours=8))
        today = datetime.now(tz).strftime('%Y-%m-%d')
        sql = f"SELECT COUNT(*) as cnt FROM user_records WHERE record_time LIKE '{today}%'"
        rows = await self.query(sql)
        if rows and 'cnt' in rows[0]:
            return rows[0]['cnt'] > 0
        return False

    async def insert_record(self, data: dict):
        """插入一条记录（使用 UTC+8 时间）"""
        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
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
    """获取用户信息并保存到 D1（每天只保留第一条）"""
    log_info("开始记录用户数据到 D1...")

    if not all([CF_ACCOUNT_ID, CF_DATABASE_ID, CF_API_TOKEN]):
        log_error("D1 配置不完整，请检查环境变量")
        return

    client = D1Client(CF_ACCOUNT_ID, CF_DATABASE_ID, CF_API_TOKEN)

    # 确保表存在
    try:
        await client.create_table_if_not_exists()
    except Exception as e:
        log_error(f"创建表失败: {e}")
        return

    # 检查今天是否已有记录
    try:
        if await client.has_record_today():
            log_wait("今天已有记录，跳过插入")
            return
    except Exception as e:
        log_error(f"检查今日记录失败: {e}")
        # 如果检查失败，继续执行插入（避免因表结构问题导致永远无法记录）
        # 但也可以直接返回，这里选择继续，但会尝试插入。

    # 获取用户信息
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

    try:
        await client.insert_record(data)
        log_success("用户记录已保存到 D1")
    except Exception as e:
        log_error(f"D1 插入失败: {e}")
        import traceback
        traceback.print_exc()
