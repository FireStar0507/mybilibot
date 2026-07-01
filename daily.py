# daily.py
import traceback
from bilibili_api import video
from tools import (
    log_info, log_success, log_error, log_wait,
    credential,
    get_or_create_bot_fav,
    get_random_follow_up,
    get_latest_video
)
from config import DEDEUSERID

async def run_daily_task():
    """
    日常任务：
    1. 获取/创建 BOT 收藏夹
    2. 重试查找有视频的 UP 主（最多 10 次）
    3. 对找到的视频执行：上报观看 20 秒 + 收藏（无点赞）
    """
    log_info("开始执行日常任务...")

    # 1. 准备收藏夹
    fav_id = await get_or_create_bot_fav(uid=int(DEDEUSERID))
    if not fav_id:
        log_error("无法获取收藏夹，日常任务终止")
        return

    # 2. 重试查找有视频的 UP 主
    max_retries = 10
    tried_uids = set()
    bvid = None

    for attempt in range(max_retries):
        up_uid = await get_random_follow_up(tried_uids)
        if not up_uid:
            log_error("没有可用的 UP 主，任务终止")
            return

        tried_uids.add(up_uid)
        bvid = await get_latest_video(up_uid)
        if bvid:
            break
        log_wait(f"UP 主 {up_uid} 没有视频，尝试下一个（{attempt+1}/{max_retries}）...")
    else:
        log_error(f"重试 {max_retries} 次后仍未找到有视频的 UP 主，任务终止")
        return

    # 3. 执行操作
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

        # 收藏（无点赞）
        await v.set_favorite(add_media_ids=[fav_id])
        log_success("添加到收藏夹完成")

        log_success("日常任务执行成功！")
    except Exception as e:
        log_error(f"处理视频时出错：{str(e)}")
        traceback.print_exc()