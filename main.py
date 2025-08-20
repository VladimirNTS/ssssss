import hashlib
import logging
import os
from datetime import datetime, timedelta
from urllib.parse import quote
from dateutil.relativedelta import relativedelta

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from starlette import status
from starlette.responses import Response
import uvicorn
from contextlib import asynccontextmanager
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats
from dotenv import load_dotenv

from handlers.user_private import create_subscription
load_dotenv()
from aiogram.types import Update
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot import bot, dp
from database.engine import session
from database.queries import (
    orm_get_user_by_id,
    orm_get_tariff,
    orm_get_last_payment_id,
    orm_new_payment,
    orm_get_payment
)
from skynetapi.skynetapi import auth, add_customer, edit_customer_date



class PayResponce(BaseModel):
    OutSum: float
    InvId: int
    Fee: float
    SignatureValue: str


async def get_session(
    session_pool: async_sessionmaker,
):
    async with session_pool() as session:
        return session
    

@asynccontextmanager
async def lifespan(app: FastAPI):
    private = [BotCommand(command='start', description='Главное меню')]

    url_webhook = f'{os.getenv("PAY_PAGE_URL")}/bot_webhook'
    await bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(private, scope=BotCommandScopeAllPrivateChats())
    await bot.set_webhook(url=url_webhook,
                          allowed_updates=dp.resolve_used_update_types(),
                          drop_pending_updates=True)
    yield
    await bot.delete_webhook()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/new_subscribe", response_class=HTMLResponse)
async def subscribe(
    request: Request,
    user_id: int,
    sub_id: int
):
    async_session = await get_session(session_pool=session)

    tariff = await orm_get_tariff(async_session, tariff_id=sub_id)
    invoice_id = await orm_get_last_payment_id(async_session) + 1
    
    base_string = f"{os.getenv('SHOP_ID')}:{tariff.price}:{invoice_id}:{os.getenv('PASSWORD_1')}"
    signature_value = hashlib.md5(base_string.encode("utf-8")).hexdigest()

    await orm_new_payment(async_session, tariff_id=tariff.id, user_id=user_id)

    return templates.TemplateResponse("/pay_new_subscribe.html", {"request": request, "price": tariff.price, "time": tariff.sub_time, "shop_id": os.getenv("SHOP_ID"), "signature_value": signature_value, "invoice_id": invoice_id})


@app.get("/new_order", response_class=HTMLResponse)
async def buy(
    request: Request,
    user_id: int,
    sub_id: int
):
    async_session = await get_session(session_pool=session)

    tariff = await orm_get_tariff(async_session, product_id=sub_id)
    invoice_id = await orm_get_last_payment_id(async_session) + 1
    base_string = f"{os.getenv('SHOP_ID')}:{tariff.price}:{invoice_id}:{os.getenv('PASSWORD_1')}"
    signature_value = hashlib.md5(base_string.encode("utf-8")).hexdigest()
    print(f"{os.getenv('SHOP_ID')}:{tariff.price}:{invoice_id}:{os.getenv('PASSWORD_1')}")
    
    await orm_new_payment(async_session, tariff_id=tariff.id, user_id=user_id)
    
    return templates.TemplateResponse("/buy_one_time.html", {"request": request, "price": tariff.price, "time": tariff.sub_time, "shop_id": os.getenv("SHOP_ID"), "signature_value": signature_value, "invoice_id": invoice_id})


@app.post("/get_payment/")
async def release(*, body: PayResponce):
    async_session = await get_session(session_pool=session)

    payment = await orm_get_payment(async_session, body.InvId)
    user = await orm_get_user_by_id(async_session, payment.user_id)
    tariff = await orm_get_tariff(async_session, payment.tariff_id)

    if not user.tun_id:
        if tariff.recuring:
            current_date = datetime.now()
            new_date = current_date + relativedelta(months=tariff.sub_time)

            new_vpn_user = await add_customer(cookies=await auth(), email=user.name, expire_time=(new_date.timestamp() * 1000), limit_ip=tariff.devices)
            await create_subscription(new_vpn_user, async_session, user.user_id, tariff, bot)
        if user.invited_by:
            pass


    return f'OK{body.InvId}'


@app.get("/continue_sub")
async def continue_sub(request: Request):
    
    async_session = await get_session(session_pool=session)

    tariff = await orm_get_tariff(async_session, tariff_id=sub_id)
    invoice_id = await orm_get_last_payment_id(async_session) + 1

    base_string = f"{os.getenv('SHOP_ID')}:{tariff.price}:{invoice_id}:{os.getenv('PASS')}"
    signature_value = hashlib.md5(base_string.encode("utf-8")).hexdigest()

    await orm_new_payment(async_session, tariff_id=tariff.id, user_id=user_id)

    return templates.TemplateResponse("/pay_new_subscribe.html", {"request": request})


@app.post("/bot_webhook")
async def webhook(request: Request) -> None:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)


@app.get("/config")
async def redirect_to_new_url(user_id: int):
    async_session = await get_session(session_pool=session)
    user = await orm_get_user_by_id(async_session, user_id=user_id)
    print(bool(user))
    if user:
        url = f'v2raytun://import/{user.tun_id}@super.skynetvpn.ru:443?type=tcp&security=tls&fp=chrome&alpn=h3%2Ch2%2Chttp%2F1.1&flow=xtls-rprx-vision#SkynetVPN-{quote(user.name)}'
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )

    uvicorn.run(app, host="0.0.0.0", port=443)

