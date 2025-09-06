from typing import Union
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from urllib.parse import quote
from dateutil.relativedelta import relativedelta
import base64
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
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
    orm_get_payment,
    orm_get_server,
    orm_get_servers,
    orm_get_user_servers,
    orm_get_user,
)
from skynetapi.skynetapi import auth, get_client, add_customer, edit_customer_date
from kbds.inline import get_inlineMix_btns

class PayResponce(BaseModel):
    OutSum: Union[str, float, int]
    InvId: Union[str, float, int]
    Fee: Union[str, float, int, None] = None
    SignatureValue: str
    EMail: Union[str, None] = None
    PaymentMethod: Union[str, None] = None
    IncCurrLabel: Union[str, None] = None
    Shp_Receipt: Union[str, None] = None


async def get_session(
    session_pool: async_sessionmaker,
):
    async with session_pool() as session:
        return session
    

@asynccontextmanager
async def lifespan(app: FastAPI):
    private = [BotCommand(command='main_menu', description='Главное меню')]

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

    time_text = ''
    if tariff.sub_time == 1:
        time_text = 'месяц'
    elif tariff.sub_time < 5:
        time_text = 'месяца'
    else:
        time_text = 'месяцев' 


    receipt =  {
          "sno":"patent",
          "items": [
            {
              "name": f"Подписка SkynetVPN на {tariff.sub_time} {time_text}",
              "quantity": 1,
              "sum": float(tariff.price),
              "payment_method": "full_payment",
              "payment_object": "service",
              "tax": "vat10"
            },
          ]
        }

    print(json.dumps(receipt, ensure_ascii=False))
    base_string = f"{os.getenv('SHOP_ID')}:{tariff.price}:{invoice_id}:{json.dumps(receipt, ensure_ascii=False)}:{os.getenv('PASSWORD_1')}"
    signature_value = hashlib.md5(base_string.encode("utf-8")).hexdigest()

    await orm_new_payment(async_session, tariff_id=tariff.id, user_id=user_id)
    
    return templates.TemplateResponse("/pay_new_subscribe.html", {"request": request, "price": tariff.price, "time": tariff.sub_time, "pay_data": json.dumps(receipt, ensure_ascii=False), "time_text": time_text,"shop_id": os.getenv("SHOP_ID"), "signature_value": signature_value, "invoice_id": invoice_id})


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


@app.post("/get_payment")
async def choose_server(
        OutSum: Union[str, float, int] = Form(...),
        InvId: Union[str, float, int] = Form(...),
        Fee: Union[str, float, int, None] = Form(None),
        SignatureValue: str = Form(...),
        EMail: Union[str, None] = Form(None),
        PaymentMethod: Union[str, None] = Form(None),
        IncCurrLabel: Union[str, None] = Form(None),
        Shp_Receipt: Union[str, None] = Form(None)
    ):
    async_session = await get_session(session_pool=session)

    payment = await orm_get_payment(async_session, InvId)
    user = await orm_get_user_by_id(async_session, payment.user_id)
    tariff = await orm_get_tariff(async_session, payment.tariff_id)
    
    btns = {}
    
    await bot.send_message(
        user.user_id,
        text="<b>Вы купили подписку на Skynet VPN</b>",
        reply_markup=get_inlineMix_btns(
            btns={'Получить ключи': f'chooseserver_{InvId}'},
            sizes=(1,)
        )
    )

    return f'OK{InvId}'


@app.get("/subscription")
async def generate_subscription_config(user_token: str):
    async_session = await get_session(session_pool=session)

    user = await orm_get_user(async_session, user_token)
    servers = await orm_get_user_servers(async_session, user.id)
    if not servers:
        raise HTTPException(status_code=404, detail="User not found or no servers available")

    subscription_headers = [
        f"#profile-title: base64:{base64.b64encode('⚡️ SkynetVPN'.encode()).decode()}",
        "#profile-update-interval: 24",
        f"#subscription-userinfo: expire={int(user.sub_end.timestamp())}", 
        "#support-url: https://t.me/skynetaivpn_support",
        "#profile-web-page-url: https://t.me/skynetaivpn_bot",
    ]

    # 3. Генерируем vless:// ссылки для каждого сервера
    config_lines = []
    for server in servers:
        server_info = await orm_get_server(async_session, server.server_id)
        cookies = await auth(server_info.server_url, server_info.login, server_info.password)
        data = await get_client(cookies, server_info.server_url, server.tun_id, server_info.indoub_id)
        client_data = data['response']
        settings = data['settings']
 
        vless_url = f'vless://{server.tun_id}@{data["ip"]}?type=tcp&security=reality&pbk={settings["settings"]["publicKey"]}&fp=chrome&sni={settings["serverNames"][0]}&sid={data["short_id"]}&spx=%2F&flow=xtls-rprx-vision#{quote(client_data["email"].split("_")[0])}'
        config_lines.append(vless_url)

    # 4. Объединяем заголовки и конфиги серверов в одну строку
    subscription_content = "\n".join(subscription_headers) + "\n" + "\n".join(config_lines)

    # 5. Возвращаем сгенерированный контент как текст.
    # FastAPI сделает это благодаря response_class=PlainTextResponse.
    
    response = Response(
        content=subscription_content,
        media_type="text/plain; charset=utf-8"
    )

    response.headers["Profile-Web-Page-Url"] = "https://t.me/skynetaivpn_bot"
    response.headers["Support-Url"] = "https://t.me/skynetaivpn_bot"

    return response


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

    if user:
        url = f'v2raytun://import/{os.getenv("PAY_PAGE_URL")}/subscription?user_token={user.user_id}'
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )

    uvicorn.run(app, host="0.0.0.0", port=443)

