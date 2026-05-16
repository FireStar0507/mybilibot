import asyncio
import random
import traceback
from bilibili_api import Credential, user, video, favorite_list
from bilibili_api.exceptions import NetworkException

SESSDATA = "b2bea5cd%2C1789560328%2C649ee%2A31CjBrssP3N3yrKfaXdp9SYcD4LqeaLHCA3sRC4rFbsHl-pEOlfDlKFCUxGGxzjT-ICgcSVlItcjQwT2tRVGswN0E4LXNacVZGSjBMWGxROVEyRG55LUtmQnFqdVZDODlZdmlDc3RUUjZ6dS1PNnBUWTNIX0V0SG9yd0tjaXFjbnNVbDFveTdraTh3IIEC"
BILI_JCT = "edbd254b5d666456acccdb6bc3fed873"
BUVID3 = "BD53345F-F5B9-1358-868D-8130574ED79C19723infoc"
DEDEUSERID = "3546700960500449"

credential = Credential(
    sessdata=SESSDATA,
    bili_jct=BILI_JCT,
    buvid3=BUVID3
)

async def get_or_create_bot_fav(uid: int):
    """获取或创建名为 BOT 的收藏夹，返回 media_id"""
    try:
        print("[日志] 获取收藏夹列表...")
        # 修正1：必须传入 uid
        lists = await favorite_list.get_video_favorite_list(uid, credential=credential)
        # 返回数据中收藏夹列表位于 'list' 键下
        for item in lists["list"]:
            if item["title"] == "BOT":
                print(f"[日志] 找到收藏夹：BOT，ID：{item['id']}")
                return item["id"]
        print("[日志] 未找到BOT收藏夹，正在创建...")
        resp = await favorite_list.create_video_favorite_list("BOT", credential=credential)
        print(f"[日志] 创建收藏夹成功，ID：{resp['id']}")
        return resp["id"]
    except Exception as e:
        print(f"[错误] 收藏夹操作失败：{str(e)}")
        traceback.print_exc()
        return None

async def get_random_follow_up():
    """从关注列表中随机选取一位UP主"""
    try:
        print("[日志] 开始获取关注列表...")
        u = user.User(uid=int(DEDEUSERID), credential=credential)
        follow_data = await u.get_followings()
        up_list = follow_data["list"]
        if not up_list:
            print("[日志] 关注列表为空")
            return None
        up_info = random.choice(up_list)
        print(f"[日志] 随机选中UP：UID={up_info['mid']}, 名称={up_info['uname']}")
        return up_info["mid"]
    except Exception as e:
        print(f"[错误] 获取关注UP失败：{str(e)}")
        traceback.print_exc()
        return None

async def get_latest_video(up_uid: int):
    """获取UP主最新视频的bvid"""
    try:
        print(f"[日志] 开始获取UP {up_uid} 的最新视频...")
        u = user.User(uid=up_uid, credential=credential)
        video_data = await u.get_videos(ps=1)
        # 视频列表在 vlist 中
        video_list = video_data.get("list", {}).get("vlist", [])
        if not video_list:
            print("[日志] 该UP主暂无视频")
            return None
        bvid = video_list[0]["bvid"]
        print(f"[日志] 获取视频成功：BV={bvid}")
        return bvid
    except NetworkException as e:
        print(f"[风控错误] 触发B站网络限制：{e}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[错误] 获取视频失败：{str(e)}")
        traceback.print_exc()
        return None

async def run_task(bvid: str, fav_id: int):
    """对视频执行点赞、收藏、上报观看进度"""
    try:
        print(f"[日志] 开始处理视频：{bvid}")
        v = video.Video(bvid=bvid, credential=credential)

        # 修正2：使用正确的方法上报观看进度（需要cid）
        # 先获取分P信息，拿到第一页的cid
        pages = await v.get_pages()
        if not pages:
            print("[错误] 无法获取视频分页信息")
            return
        cid = pages[0]["cid"]  # 第一页的cid
        print(f"[日志] 获取cid: {cid}")

        # 上报观看进度（模拟观看20秒，视频总时长假设为300秒，可从pages[0]["duration"]获取）
        await v.report_watch_history(progress=20, cid=cid)
        print("[日志] 上报观看20秒完成")

        # 点赞
        await v.like(True)
        print("[日志] 点赞视频完成")

        # 收藏（注意参数名 add_media_ids）
        await v.set_favorite(add_media_ids=[fav_id])
        print("[日志] 添加到收藏夹完成")

        print("[完成] 视频处理成功！")
    except Exception as e:
        print(f"[错误] 处理视频失败：{str(e)}")
        traceback.print_exc()

async def main():
    print("=== 脚本启动 ===")
    # 获取随机UP主
    up_uid = await get_random_follow_up()
    if not up_uid:
        print("=== 脚本结束：未获取到UP主 ===")
        return

    # 获取最新视频
    bvid = await get_latest_video(up_uid)
    if not bvid:
        print("=== 脚本结束：未获取到视频 ===")
        return

    # 获取或创建收藏夹（需要传入当前用户的uid）
    fav_id = await get_or_create_bot_fav(uid=int(DEDEUSERID))
    if not fav_id:
        print("=== 脚本结束：无法获取收藏夹 ===")
        return

    # 执行点赞收藏上报
    await run_task(bvid, fav_id)
    print("=== 脚本全部执行完毕 ===")

if __name__ == '__main__':
    asyncio.run(main())
