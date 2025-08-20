import asyncio
import os
import aiohttp
import uuid

from database.queries import orm_get_user

headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'https://super.skynetvpn.ru:8080',
    'Referer': 'https://super.skynetvpn.ru:8080/paneladmin/panel/inbounds',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    # 'Cookie': 'lang=ru-RU; ...',
}

async def auth():
    data = {
        'username': os.getenv('SKY_USERNAME'),
        'password': os.getenv('SKY_PASSWORD'),
        'twoFactorCode': '',
    }
    print(data)

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post('https://super.skynetvpn.ru:8080/paneladmin/login', data=data) as response:
            text = await response.text()
            print(text)
            cookies = response.cookies
            return cookies


async def add_customer(cookies, email, expire_time, limit_ip):
    id = uuid.uuid4()
    sub_id = str(uuid.uuid4()).split('-')[0]

    data = {
        'id': '1',
        'settings': '{"clients": [{\n  "id": "%s",\n  "flow": "",\n  "email": "%s",\n  "limitIp": %s,\n  "totalGB": 0,\n  "expiryTime": %s,\n  "enable": true,\n  "tgId": "",\n  "subId": "%s",\n  "comment": "",\n  "reset": 0\n}]}' % (id, email, limit_ip, expire_time, sub_id)
    }

    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        async with session.post(
            'https://super.skynetvpn.ru:8080/paneladmin/panel/inbound/addClient',
            data=data,
        ) as response:
            text = await response.text()
            return {
                "response": text,
                "email": email,
                "expire_time": expire_time,
                "id": id,
                "sub_id": sub_id
            }


async def edit_customer_date(cookies, expire_time, id, session):

    user = orm_get_user(session, id)

    data = {
        'id': '1',
        'settings': '{"clients": [{\n  "id": "%s",\n  "flow": "xtls-rprx-vision",\n  "email": "%s",\n  "limitIp": 0,\n  "totalGB": 0,\n  "expiryTime": %s,\n  "enable": true,\n  "tgId": "",\n  "subId": "%s",\n  "comment": "",\n  "reset": 0\n}]}' % (user.tun_id, user.name, expire_time, user.sub_id),
    }

    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        async with session.post(
            f'https://super.skynetvpn.ru:8080/paneladmin/panel/inbound/updateClient/{user.tun_id}',
            data=data,
        ) as response:
            text = await response.text()
            return {
                "response": text,
                "expire_time": expire_time,
                "id": id,
            }








