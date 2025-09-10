import json
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

async def auth(server, login, password):
    data = {
        'username': login,
        'password': password,
        'twoFactorCode': '',
    }
    print(data)

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(server + 'login', data=data) as response:
            text = await response.text()
            cookies = response.cookies
            print(cookies)
            return cookies


async def add_customer(server, indoub_id, cookies, email, expire_time, limit_ip, chat_id, username):
    uu_id = str(uuid.uuid4())
    sub_id = str(uuid.uuid4()).split('-')[0]

    client_obj = {
        "id": uu_id,
        "flow": "xtls-rprx-vision",
        "email": email,
        "limitIp": int(limit_ip),
        "totalGB": 0,
        "expiryTime": int(expire_time),
        "enable": True,
        "subId": uu_id.split('-')[-1],
        "comment": str(username),
        "reset": 0
    }
    
    settings_obj = {
        "clients": [client_obj]
    }
    
    settings_str = json.dumps(settings_obj, ensure_ascii=False)
    print(settings_str)
    data = {
        'id': str(indoub_id),
        'settings': settings_str
    }
    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        async with session.post(
            server + 'panel/inbound/addClient',
            data=data,
        ) as response:
            text = await response.text()
            
            print('Ответ:', response, text)
            with open('log.txt', 'w') as f:
                f.write(str(data) + str(response) + str(text))

            return {
                "response": text,
                "email": email,
                "expire_time": expire_time,
                "id": uu_id,
                "sub_id": sub_id
            }


async def edit_customer_date(server, cookies, expire_time, tun_id, session):
    client = await get_client(cookies, server.server_url, tun_id, server.indoub_id)
    client_obj = {
        "id": tun_id,
        "flow": "xtls-rprx-vision",
        "email": client['response']['email'],
        "limitIp": client['response']['limitIp'],
        "totalGB": 0,
        "expiryTime": int(expire_time),
        "enable": True,
        "comment": client['response']['comment'],
        "subId": client['response'].get('subId', ''),
        "reset": 0
    }
    
    settings_obj = {
        "clients": [client_obj]
    }
    
    settings_str = json.dumps(settings_obj)
    print(settings_str)

    data = {
        'id': server.indoub_id,
        'settings': settings_str,
    }

    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        async with session.post(
            server.server_url + f'panel/api/inbounds/updateClient/{tun_id}',
            data=data,
        ) as response:
            with open('log.txt', 'w') as f:
                f.write(str(int(expire_time)))
            text = await response.text()
            return {
                "response": text,
                "expire_time": expire_time,
                "id": id,
            }



async def edit_customer_limit_ip(server, cookies, limit_ip, id, session, tun_id):
    client = await get_client(cookies, server.server_url, tun_id, server.indoub_id)
    
    with open('log.txt', 'w') as f:
        f.write(str(client))
    
    client_obj = {
        "id": tun_id,
        "flow": "xtls-rprx-vision",
        "email": client['response']['email'],
        "limitIp": int(limit_ip),
        "totalGB": 0,
        "expiryTime": client['response']['expiryTime'],
        "enable": True,
        "comment": client['response']['comment'],
        "subId": client['response'].get('subId', ''),
        "reset": 0
    }
    
    settings_obj = {
        "clients": [client_obj]
    }
    
    settings_str = json.dumps(settings_obj)
    print(settings_str)

    data = {
        'id': server.indoub_id,
        'settings': settings_str,
    }

    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        async with session.post(
            server.server_url + f'panel/api/inbounds/updateClient/{tun_id}',
            data=data,
        ) as response:
            print(response.json())
            text = await response.text()
            return {
                "response": text,
                "id": id,
            }


async def get_client(cookies, server, tun_id, inbound):
    
    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        async with session.get(
            server + f'panel/api/inbounds/get/{inbound}',
        ) as response:
            json_resp = await response.json()
            clients = json.loads(json_resp['obj']['settings'])['clients']
            pbi = json.loads(json_resp['obj']['streamSettings'])['realitySettings']
            short_id = json.loads(json_resp['obj']['streamSettings'])['realitySettings']['shortIds'][0]
            
            for client in clients:
                if client['id'] == tun_id:
                    return {
                        "response": client,
                        "settings": pbi,
                        "ip": json_resp['obj']['tag'].split('-')[-1],
                        "short_id": short_id
                    }


async def delete_customer(server, cookies, user_uuid):

    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        async with session.post(
            server.server_url + f'panel/api/inbounds/{server.indoub_id}/delClient/{user_uuid}',
        ) as response:
            print(response.json())
            text = await response.text()
            return {
                "response": text,
            }





