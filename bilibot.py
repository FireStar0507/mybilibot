import asyncio
import random
import time
import traceback
from datetime import datetime
from bilibili_api import Credential, user, video, favorite_list
from bilibili_api.exceptions import NetworkException

# ========== 你的 Cookie 信息 ==========
SESSDATA = "b2bea5cd%2C1789560328%2C649ee%2A31CjBrssP3N3yrKfaXdp9SYcD4LqeaLHCA3sRC4rFbsHl-pEOlfDlKFCUxGGxzjT-ICgcSVlItcjQwT2tRVGswN0E4LXNacVZGSjBMWGxROVEyRG55LUtmQnFqdVZDODlZdmlDc3RUUjZ6dS1PNnBUWTNIX0V0SG9yd0tjaXFjbnNVbDFveTdraTh3IIEC"
BILI_JCT = "edbd254b5d666456acccdb6bc3fed873"
BUVID3 = "BD53345F-F5B9-1358-868D-8130574ED79C19723infoc"
DEDEUSERID = "3546700960500449"
# ==================================

credential = Credential(
    sessdata=SESSDATA,
    bili_jct=BILI_JCT,
    buvid3=BUVID3
)

def log_info(msg: str):
    print(f"[*] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def log_success(msg: str):
    print(f"[+] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def log_error(msg: str):
    print(f"[!] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def log_wait(msg: str):
    print(f"[?] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

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

        # 过滤掉已经尝试过的 UID
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

async def run_task(bvid: str, fav_id: int):
    """对视频执行收藏和上报观看（无点赞）"""
    try:
        log_info(f"处理视频：{bvid}")
        v = video.Video(bvid=bvid, credential=credential)

        # 获取 cid
        pages = await v.get_pages()
        if not pages:
            log_error("无法获取视频分页信息")
            return
        cid = pages[0]["cid"]
        log_info(f"获取 cid: {cid}")

        # 上报观看 20 秒
        await v.report_watch_history(progress=20, cid=cid)
        log_success("上报观看 20 秒完成")

        # 收藏（注意：无点赞）
        await v.set_favorite(add_media_ids=[fav_id])
        log_success("添加到收藏夹完成")

        log_success("视频处理成功！")
    except Exception as e:
        log_error(f"处理视频失败：{str(e)}")
        traceback.print_exc()

async def main():
    log_info("=== 脚本启动 ===")

    # 1. 随机延迟 0~600 秒（实现北京时间 6:00 ±10 分钟）
    delay = random.randint(0, 600)
    log_wait(f"随机延迟 {delay} 秒后开始执行...")
    await asyncio.sleep(delay)

    # 2. 准备收藏夹
    fav_id = await get_or_create_bot_fav(uid=int(DEDEUSERID))
    if not fav_id:
        log_error("无法获取收藏夹，脚本退出")
        return

    # 3. 重试查找有视频的 UP 主（最多 10 次）
    max_retries = 10
    tried_uids = set()
    bvid = None

    for attempt in range(max_retries):
        up_uid = await get_random_follow_up(tried_uids)
        if not up_uid:
            log_error("没有可用的 UP 主，脚本退出")
            return

        tried_uids.add(up_uid)
        bvid = await get_latest_video(up_uid)
        if bvid:
            break
        log_wait(f"UP 主 {up_uid} 没有视频，尝试下一个（{attempt+1}/{max_retries}）...")
    else:
        log_error(f"重试 {max_retries} 次后仍未找到有视频的 UP 主，脚本退出")
        return

    # 4. 执行任务
    await run_task(bvid, fav_id)
    log_success("=== 全部完成 ===")

if __name__ == '__main__':
    asyncio.run(main())
