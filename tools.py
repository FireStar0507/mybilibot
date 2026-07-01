# tools.py
import asyncio
import random
import traceback
from datetime import datetime
from bilibili_api import Credential, user, favorite_list
from bilibili_api.exceptions import NetworkException
from config import SESSDATA, BILI_JCT, BUVID3, DEDEUSERID

# ---------- 日志函数 ----------
def log_info(msg: str):
    print(f"[*] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def log_success(msg: str):
    print(f"[+] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def log_error(msg: str):
    print(f"[!] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def log_wait(msg: str):
    print(f"[?] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

# ---------- 全局凭证 ----------
credential = Credential(
    sessdata=SESSDATA,
    bili_jct=BILI_JCT,
    buvid3=BUVID3
)

# ---------- 收藏夹操作 ----------
async def get_or_create_bot_fav(uid: int):
    """获取或创建名为 BOT 的收藏夹，返回 media_id"""
    try:
        log_info("获取收藏夹列表...")
        lists = await favorite_list.get_video_favorite_list(uid, credential=credential)
        for item in lists["list"]:
            if item["title"] == "BOT":
                log_success(f"找到收藏夹：BOT，ID：{item['id']}")
                return item["id"]
        log_wait("未找到 BOT 收藏夹，正在创建...")
        resp = await favorite_list.create_video_favorite_list("BOT", credential=credential)
        log_success(f"创建收藏夹成功，ID：{resp['id']}")
        return resp["id"]
    except Exception as e:
        log_error(f"收藏夹操作失败：{str(e)}")
        traceback.print_exc()
        return None

# ---------- UP 主和视频获取 ----------
async def get_random_follow_up(exclude_uids: set):
    """从关注列表中随机选取一位未尝试过的 UP 主"""
    try:
        log_info("获取关注列表...")
        u = user.User(uid=int(DEDEUSERID), credential=credential)
        follow_data = await u.get_followings()
        up_list = follow_data.get("list", [])
        if not up_list:
            log_error("关注列表为空")
            return None

        available = [up for up in up_list if up["mid"] not in exclude_uids]
        if not available:
            log_error("所有关注 UP 主均已尝试过，没有更多可选")
            return None

        up_info = random.choice(available)
        log_success(f"随机选中 UP：UID={up_info['mid']}, 名称={up_info['uname']}")
        return up_info["mid"]
    except Exception as e:
        log_error(f"获取关注 UP 失败：{str(e)}")
        traceback.print_exc()
        return None

async def get_latest_video(up_uid: int):
    """获取 UP 主最新视频的 bvid，如果没有视频则返回 None"""
    try:
        log_info(f"获取 UP {up_uid} 的最新视频...")
        u = user.User(uid=up_uid, credential=credential)
        video_data = await u.get_videos(ps=1)
        video_list = video_data.get("list", {}).get("vlist", [])
        if not video_list:
            log_wait("该 UP 主暂无视频")
            return None
        bvid = video_list[0]["bvid"]
        log_success(f"获取视频成功：{bvid}")
        return bvid
    except NetworkException as e:
        log_error(f"网络限制：{e}")
        return None
    except Exception as e:
        log_error(f"获取视频失败：{str(e)}")
        traceback.print_exc()
        return None