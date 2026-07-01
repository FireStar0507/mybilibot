# main.py
import asyncio
import random
from tools import log_info, log_success, log_wait
from daily import run_daily_task
from record import save_user_record

async def main():
    log_info("=== 程序启动 ===")

    delay = random.randint(0, 600)
    log_wait(f"随机延迟 {delay} 秒后开始执行...")
    await asyncio.sleep(delay)

    await run_daily_task()
    await save_user_record()   # 记录数据到 D1

    log_success("=== 程序结束 ===")

if __name__ == '__main__':
    asyncio.run(main())
