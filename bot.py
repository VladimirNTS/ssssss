from datetime import datetime, date
import os
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import BotCommand, BotCommandScopeDefault

from handlers.user_private import user_private_router
from handlers.admin_private import admin_private_router
from database.engine import session, create_db
from middlewares.db_session import DataBaseSession
from database.queries import (
    orm_get_users,
    orm_get_tariff
)

bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher()

dp.include_router(user_private_router)
dp.include_router(admin_private_router)



async def check_sub():
    with session() as async_session:
        users = orm_get_users(async_session)
        for user in users:
            user_end_date = user.sub_end
            today = date.today()

            if user_end_date is None:
                continue

            days_left = (user_end_date - today).days
            tartiff = await orm_get_tariff(async_session, user.status)

            if days_left == 5 and tariff.sub_time>10 and tariff.recuring and status:
                bot.send_message(
                    user.user_id,
                    "Срок вашей подписки истекает через 5 дней",
                    reply_markup=get_inlineMix_btns(
                        btns={'Продлить': f'{os.getenv("PAY_PAGE_URL")}/continie_sub?user_id={user.id}','Отменить': f'cancelsub_{user.id}'}
                    )
                )
            elif days_left == 1 and tariff.recuring and status:
                bot.send_message(
                    user.user_id,
                        "Срок вашей подписки истекает через 1 день",
                        reply_markup=get_inlineMix_btns(
                            btns={'Продлить': f'{os.getenv("PAY_PAGE_URL")}/continie_sub?'}
                        )
                    )

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_sub, 'cron', hour=0)
    scheduler.start()

    await create_db()
    dp.update.middleware.register(DataBaseSession(session_pool=session))
    #await dp.start_polling(bot)

asyncio.run(main())

