import uuid
from datetime import datetime

from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
import time
import os
from urllib.parse import quote
from dateutil.relativedelta import relativedelta

import qrcode
from filters.users_filter import BlockedUsersFilter

from kbds.inline import get_callback_btns, get_inlineMix_btns, get_url_btns
from database.queries import (
    orm_change_user_status,
    orm_get_tariff,
    orm_get_tariffs,
    orm_get_faq,
    orm_get_user,
    orm_get_user_by_id,
    orm_add_user,
    orm_change_user_server,
    orm_get_servers,
    orm_get_server,
    orm_add_server,
    orm_edit_server,
    orm_end_payment,
    orm_get_payment,
    orm_get_user_servers,
)
from skynetapi.skynetapi import auth, add_customer, edit_customer_date, get_client, delete_customer

user_private_router = Router()
user_private_router.message.filter(BlockedUsersFilter())


@user_private_router.message(Command('start'))
async def start(message, session):
    args = message.text.split()[1:]
    if args:
        await orm_add_user(session=session, user_id=message.from_user.id, name=message.from_user.username or message.from_user.first_name, invited_by=args[0])
    else:
        await orm_add_user(session=session, user_id=message.from_user.id, name=message.from_user.username or message.from_user.first_name, invited_by=None)

    await message.answer_photo(
        photo=types.FSInputFile("img/banner.png"),
        caption='<b>SkynetVPN — сервис защищённых подключений.</b>\n\n<b>Используя бота, вы подтверждаете, что ознакомились и принимаете условия <a href="https://skynetvpn.ru/terms-of-service.html">Публичной оферты</a> и <a href="https://skynetvpn.ru/terms-of-service.html">Политики обработки персональных данных</a>.</b>\n\nСервис не предназначен для обхода ограничений доступа к информации. Получение/распространение запрещённой информации в РФ запрещено.\n\nМы предоставляем техническую услугу по организации шифрованного соединения и не формируем/не контролируем содержимое трафика.\n\nПользователь обязуется соблюдать законодательство РФ (в т.ч. 149-ФЗ, 114-ФЗ, 436-ФЗ, 187-ФЗ).',
        reply_markup=get_inlineMix_btns(
            btns={
                "Оферта": "https://skynetvpn.ru/terms-of-service.html",
                "Политика ПДН": "https://skynetvpn.ru/privacy-policy.html",
                "Продолжить": "back_menu"
            }
        )
    )


@user_private_router.message(Command("main_menu"))
async def start(message: types.Message, session):
    btns = {
                "📡 Подключить": "choosesubscribe",
                "🔍 Проверить подписку": "check_subscription",
                "📲 Установить VPN": "install",
                "👫 Пригласить": "referral_program",
                "❓ FAQ": "faq", "☎ Поддержка": "https://t.me/skynetaivpn_support",
                "🛒 Другие продукты": "other_products",
                "📄 Оферта | Политика": "about"
    }
    if message.from_user.id == int(os.getenv("OWNER")):
        btns["Админ панель"] = "admin"


    await message.answer_photo(
        photo=types.FSInputFile("img/banner.png"),
        caption="<b>SkyNetVPN — сервис шифрованных подключений.</b>\n\nМы не анализируем содержимое трафика и не ведём его содержательные логи. \n\nУстанавливается на:  <b>Windows / macOS / iOS / Android / Linux / Android TV. </b>\n\nТрафик со стороны сервиса не лимитируется. \nФактическая скорость соединения зависит от вашей сети и устройства.\n\n<b>Оплатите тариф и начинайте пользоваться.</b>", 
        reply_markup=get_inlineMix_btns(
            btns=btns,
            sizes=(1,1,1,1,2,2)
        )
    )


@user_private_router.callback_query(F.data=='about')
async def about(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption='<b>О нас:</b>\n\nМы предоставляем техническую услугу по организации шифрованного соединения (VPN). Не являемся СМИ, не размещаем и не контролируем контент. Сервис не предназначен для обхода ограничений и доступа к запрещённой информации.\n\nПолный текст — <a href="https://skynetvpn.ru/privacy-policy.html">Политика конфидециальности</a>.\n\nХарактеристики, сроки и стоимость — в интерфейсе бота и в <a href="https://skynetvpn.ru/terms-of-service.html">Публичной оферте</a>.\n\n<b>Исполнитель</b>: \nИП Мелконьян Елена Павловна, ИНН 232017219889, ОГРНИП 324237500172507.\n\n<b>Контакты оператора ПДн</b>: \ne-mail: 555cent@mail.ru.',
        reply_markup=get_inlineMix_btns(
                    btns={"⬅ Назад": "back_menu"},
                    sizes=(1,)
                 )
    )



@user_private_router.callback_query(F.data=='back_menu')
async def back_menu(callback: types.CallbackQuery):
    btns = {
                "📡 Подключить": "choosesubscribe",
                "🔍 Проверить подписку": "check_subscription",
                "📲 Установить VPN": "install",
                "👫 Пригласить": "referral_program",
                "❓ FAQ": "faq", "☎ Поддержка": "https://t.me/skynetaivpn_support",
                "🛒 Другие продукты": "other_products",
                "📄 Оферта | Политика ПДн": "about"
    }
    photo = types.InputMediaPhoto(
			media=types.FSInputFile("img/banner.png"),  # или BufferedInputFile для файла в памяти
			caption=f"<b>SkynetVPN — сервис защищённых подключений.</b>\n\nМы не анализируем содержимое трафика и не ведём его содержательные логи.\n\nТрафик со стороны сервиса не лимитируется; фактическая скорость зависит от сети и устройства.\n\n<b>Оплатите тариф и начинайте пользоваться.</b>"
		)
	
    try:
        await callback.message.edit_media(
            media=photo,
            reply_markup=get_inlineMix_btns(
                btns=btns, 
                sizes=(1,1,1,1,2)
            )
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
            return
        raise


@user_private_router.callback_query(F.data.startswith('choosesubscribe'))
async def choose_subscribe(callback: types.CallbackQuery, session):
    user = await orm_get_user(session, callback.from_user.id)
    tariffs = await orm_get_tariffs(session)
    btns = {}

    servers = await orm_get_servers(session)
    countries = ''

    for i in range(0, len(servers)):
        if i == len(servers)-1:
            countries += f'└ {servers[i].name}'
        else:
            countries += f'├ {servers[i].name}\n'

        
    for i in tariffs:
        if i.recuring:
            btns[f"{i.sub_time} мес., {i.price} ₽, кол. устройств {i.devices}"] = f"chousen_{i.id}|{user.id}"
        else:
            pass

    btns["⬅ Назад"] = "back_menu"
    
    try:
        await callback.message.edit_caption(caption=f"<b>⚡️ Вы покупаете премиум подписку на Skynet VPN</b>\n\n● Возможность подключить любые устройства\n● До 4 устройств одновременно \n● Без лимитов и ограничений по скорости\n\n<b>Список поддерживаемых устройств:</b>\n\n<b>Android</b> (Android 7.0 или новее.) | <b>Windows</b> (Windows 8.1 или новее.) | <b>iOS, iPadOS</b> (iOS 16.0 или новее.) | <b>macOS</b> процессоры M  (macOS 13.0 или новее) | <b>macOS</b>  c процессором Intel (macOS 11.0 или новее.) | <b>Android TV</b> ( Android 7.0 или новее.) | <b>Linux</b>\n\n🌍 <b>Доступные страны:</b>\n👑 - без рекламы на YouTube\n🎧 - YouTube можно сворачивать\n\n{countries}", reply_markup=get_inlineMix_btns(btns=btns, sizes=(1,)))
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
            return
        raise


@user_private_router.callback_query(F.data.startswith('chousen_'))
async def show_chousen(callback, session):
    try:
        tariff = await orm_get_tariff(session, callback.data.split('_')[-1].split('|')[0])
        
        await callback.message.edit_caption(
            caption=f"Вы выбрали подписку: <b>{tariff.sub_time} мес.</b>\nСтоимость: <b>{tariff.price} руб.</b>\nСпособ оплаты: <b>Банковская карта</b>\nВремя на оплату: <b>10 минут</b>\n\nВсе подписки продлеваются автоматически. Отмена подписки возможна в любой момент.\n\nПосле оплаты <b>SkynetVPN будет отправлена в течение минуты.</b>",
            reply_markup=get_inlineMix_btns(
                btns={
                    'Оплатить': f"{os.getenv('PAY_PAGE_URL')}/new_subscribe?user_id={callback.data.split('_')[-1].split('|')[1]}&sub_id={tariff.id}", 
                    'Назад': 'choosesubscribe'
                }
            )
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
            return
        raise


@user_private_router.callback_query(F.data == 'referral_program')
async def referral_program_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await callback.bot.me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"

    
    # Генерируем уникальное имя файла
    timestamp = int(time.time())
    qr_filename = f"qr_{user_id}_{timestamp}.png"
    
    # Создаем QR-код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(referral_link)
    qr.make(fit=True)
    
    # Сохраняем QR-код в файл
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_filename)
    
    try:
        # Отправляем файл пользователю
        photo = types.InputMediaPhoto(
			media=types.FSInputFile(qr_filename),  # или BufferedInputFile для файла в памяти
			caption=f"Приглашайте друзей и получайте бонусы:\n\n<b>За каждую покупку приглашенных пользователей Вы получите к вашей подписке:</b>\n\nЗа 1 мес. – 15 дней\nЗа 6 мес. – 30 дней\nЗа 12 мес. – 45 дней\n\n<b>Ваша реферальная ссылка:</b>\n<code>{referral_link}</code>"
		)
        try:
            await callback.message.edit_media(media=photo, reply_markup=get_callback_btns(btns={ "⬅ Назад": "back_menu"}))
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
                return
            raise
        await callback.answer()
    finally:
        # Удаляем файл после отправки (если он существует)
        if os.path.exists(qr_filename):
            os.remove(qr_filename)

    
# FAQ
@user_private_router.callback_query(F.data == "faq")
async def orders_list(callback: types.CallbackQuery, session):
    await callback.answer()
    message_text = "<b>Часто задаваемые вопросы</b>\n\n"
    orders = await orm_get_faq(session)
    number = 1
    for order in orders:
        message_text += f"{number}. {order.ask} \n{order.answer}\n\n"
        number += 1
    try:
        await callback.message.edit_caption(
            caption=message_text,
            reply_markup=get_callback_btns(btns={ "⬅ Назад": "back_menu"})
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise


@user_private_router.callback_query(F.data.startswith('other_products'))
async def other_products(callback: types.CallbackQuery, session):
        try:
            await callback.message.edit_caption(
                caption="Другие продукты:",
                reply_markup=get_inlineMix_btns(btns={
                    "Скачивание видео из соцсетей": "https://t.me/Skynet_download_bot",
                    "Наш телеграм канал": "https://t.me/Sky_Net_AI",
                    "⬅ Назад": "back_menu"
                    }, sizes=(1,))
                 )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return

# Check subscription
@user_private_router.callback_query(F.data.startswith('check_subscription'))
async def check_subscription(callback: types.CallbackQuery, session): 
    user_id = callback.from_user.id
    user = await orm_get_user(session, user_id)
    user_servers = await orm_get_user_servers(session, user.id)
    if user.status > 0:
    
        tariff = await orm_get_tariff(session, user.status)
        with open('log.txt', 'w') as f:
            f.write(str(user.server) + " " + str(user.name))
    
        url = f"{os.getenv('PAY_PAGE_URL')}/subscription?user_token={callback.from_user.id}"
        
        try:
            time_text = 'месяц'
            if tariff.sub_time > 1 and tariff.sub_time < 5:
                time_text = 'месяца'
            elif tariff.sub_time >= 5:
                time_text = 'месяцев'

            await callback.message.edit_caption(
                caption=f"<b>⚙️ Ваша подписка SkynetVPN</b>: \n├ оплачено до <b>{user.sub_end.date()}</b> \n└ Цена <b>{tariff.price} ₽ за {tariff.sub_time} {time_text}</b>\n\nВаша ссылка для подключения, нажмите 1 раз чтобы скопировать:\n <code>{url}</code>",
                reply_markup=get_inlineMix_btns(btns={"🛜 Подключиться v2rayRun": f'{os.getenv("PAY_PAGE_URL")}/config?user_id={user.id}', '🚫 Отменить подписку': 'cancelsub_{user_id}', "⬅ Назад": "back_menu"}, sizes=(1,))
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
            raise
    elif user_servers:
        tariff = await orm_get_tariff(session, user.status)
        with open('log.txt', 'w') as f:
            f.write(str(user.server) + " " + str(user.name))

        url = f"{os.getenv('PAY_PAGE_URL')}/subscription?user_token={callback.from_user.id}"
        
        try:
            await callback.message.edit_caption(
                caption=f"<b>⚙️ Ваша подписка SkynetVPN</b>: \n└ оплачено до <b>{user.sub_end.date()}</b>\n\n<b>⚠️ Ваша подписка отменена и больше не будет автоматически продлеваться.</b>\n\nВаша ссылка для подключения, нажмите 1 раз чтобы скопировать: \n<code>{url}</code>",
                reply_markup=get_inlineMix_btns(btns={"🛜 Подключиться v2rayRun": f'{os.getenv("PAY_PAGE_URL")}/config?user_id={user.id}', "Продлить подписку": "choosesubscribe", "⬅ Назад": "back_menu"}, sizes=(1,))
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
           
    else:
        await callback.answer("У вас нет активной подписки", show_alert=True)



@user_private_router.callback_query(F.data == 'changeserver')
async def change_server(callback: types.CallbackQuery, session):
    btns = {}
    servers = await orm_get_servers(session)

    for i in servers:
        btns[i.name] = f'changesubscribe_{i.id}'
    
    btns['⬅ Назад'] = 'check_subscription'

    try:
        await callback.message.edit_caption(
            caption="<b>🔄 Смена сервера</b>\nПосле выбора нового сервера вам будет отправлен новый ключ доступа.\n\nВыберите новый сервер:\n\n👑 - без рекламы на YouTube\n🎧 - YouTube можно сворачивать",
            reply_markup=get_inlineMix_btns(
                btns=btns,
                sizes=(1,)
            )
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
            return
        raise



@user_private_router.callback_query(F.data.startswith('changesubscribe_'))
async def change_tariff(callback, session):
    user = await orm_get_user(session, callback.from_user.id)
    server = await orm_get_server(session, user.server)

    cookies = await auth(server.server_url, server.login, server.password)
    await delete_customer(server, cookies, user.tun_id)

    await orm_change_user_server(session, user.id, int(callback.data.split('_')[-1]))

    server = await orm_get_server(session, user.server)
    tariff = await orm_get_tariff(session, user.status)


    new_vpn_user = await add_customer(
        server.server_url,
        server.indoub_id,
        cookies, 
        server.name + '_' + str(user.id),
        (user.sub_end.timestamp() * 1000),
        tariff.devices,
        user.user_id,
        callback.from_user.username or user.name
    )

    await orm_change_user_status(session, user_id=user.id, new_status=tariff.id, tun_id=str(new_vpn_user['id']), sub_end=user.sub_end)
    await check_subscription(callback, session)


@user_private_router.callback_query(F.data.startswith('cancelsub_'))
async def cancel_subscription(callback, session):
    try:
        user = await orm_get_user(session, callback.from_user.id)
        
        await orm_change_user_status(session, user.id, 0, user.sub_end, user.tun_id)
        await callback.answer("Подписка отменена", show_alert=True)
        await check_subscription(callback, session)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise


@user_private_router.callback_query(F.data == 'install')
async def install_helper(callback: types.CallbackQuery, session):
    try:
        await callback.message.edit_caption(
            caption="<b>Выберите своё устройство</b>: \n\nСделали пошаговые инструкции для подключения VPN! Нажмите на нужную кнопку и подключайтесь за несколько минут.",
            reply_markup=get_callback_btns(btns={'📱 Android': 'help_android', '🍏 Iphone': 'help_iphone', '🖥 Windows': 'help_windows', '💻 MacOS': 'help_macos', '🐧 Linux': 'help_linux', '📺 AndroidTV': 'help_androidtv', "⬅ Назад": "back_menu"}, sizes=(2,2,2,1))
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Изменений нет")
            return
        raise


@user_private_router.callback_query(F.data == 'install_mes')
async def install_helper(callback: types.CallbackQuery, session):
    try:
        await callback.message.answer_photo(
            photo=types.FSInputFile("img/banner.png"),
            text="<b>Выберите своё устройство</b>: \n\nСделали пошаговые инструкции для подключения VPN! Нажмите на нужную кнопку и подключайтесь за несколько минут.",
            reply_markup=get_callback_btns(btns={'📱 Android': 'help_android', '🍏 Iphone': 'help_iphone', '🖥 Windows': 'help_windows', '💻 MacOS': 'help_macos', '🐧 Linux': 'help_linux', '📺 AndroidTV': 'help_androidtv', "⬅ Назад": "back_menu"}, sizes=(2,2,2,1))
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Изменений нет")
            return
        raise


@user_private_router.callback_query(F.data.startswith('help_'))
async def install(callback):
    text = {
            'android': '<b>📖 Для подключения VPN на Android:</b>\n\n1. Установите приложение «v2RayTun» из Google Play по кнопке ниже.\n\n2. Нажмите кнопку «🔗 Добавить профиль», чтобы добавить подключение в приложение.\n\n3. Всё готово! Теперь вы под защитой и можете без преград пользоваться интернетом!|||https://play.google.com/store/apps/details?id=com.v2raytun.android&pcampaignid=web_share',
            'iphone': '<b>📖 Для подключения VPN на Iphone:</b>\n\n1. Установите приложение «v2RayTun» из App Store по кнопке ниже.\n\n2. Нажмите кнопку «🔗 Добавить профиль», чтобы добавить подключение в приложение.\n\n3. Всё готово! Теперь вы под защитой и можете без преград пользоваться интернетом!|||https://apps.apple.com/ru/app/v2raytun/id6476628951',
            'windows': '<b>Инструкция для Windows:</b>\n\n1. Скопировать ключ, который вы получили\n\n2. Запустить приложение v2raytun от имени администратора (1 СКРИН )\n\n3. Вверху справа нажать "+" и выбрать первое предложенное "Импортировать из буфера обмена" или на английском: "Import from clickboard"  (2 СКРИН)\n\n4. Зайти в Настройки – Настройки трафика – Режим – Туннель (3 СКРИН)\n\n5. Вернуться в главное меню, проверить появился ли ключ и запустить ВПН (4 СКРИН)\n\n6. Всё готово! Теперь вы под защитой и можете без преград пользоваться интернетом!|||https://storage.v2raytun.com/v2RayTun_Setup.exe',
            'macos': '<b>📖 Для подключения VPN на MacOS:</b>\n\n1. Установите приложение «v2RayTun» из App Store по кнопке ниже.\n\n2. Нажмите кнопку «🔗 Добавить профиль», чтобы добавить подключение в приложение.\n\n3. Всё готово! Теперь вы под защитой и можете без преград пользоваться интернетом!|||https://apps.apple.com/ru/app/v2raytun/id6476628951',
            'linux': '<b>📖 Для подключения VPN на Linux:</b>\n\n1. Скачайте приложение Hiddify по кнопке ниже и установите его на ваш компьютер.\n\n2. Нажмите кнопку «🔗 Добавить профиль», чтобы добавить подключение в приложение.\n\n3. Всё готово! Теперь вы под защитой и можете без преград пользоваться интернетом!|||https://github.com/hiddify/hiddify-app/releases/latest/download/Hiddify-Linux-x64.AppImage',
            'androidtv': '<b>📖 Для подключения VPN на Android:</b>\n\n1. Установите приложение «v2RayTun» из Google Play по кнопке ниже.\n\n2. Нажмите кнопку «🔗 Добавить профиль», чтобы добавить подключение в приложение.\n\n3. Всё готово! Теперь вы под защитой и можете без преград пользоваться интернетом!|||https://play.google.com/store/apps/details?id=com.v2raytun.android&pcampaignid=web_share',
            }
    
    try:
        if callback.data.split('_')[-1].split('|||')[0] == 'windows':

            media = [
                types.InputMediaPhoto(
                    media=types.FSInputFile("img/instruction_windows_1.jpg"), 
                    caption=text[callback.data.split('_')[-1]].split('|||')[0],
                    reply_markup=get_inlineMix_btns(
                        btns={"Установить": text[callback.data.split('_')[-1]].split('|||')[1], "Подключиться": 'check_subscription', "⬅ Назад": "install"},
                        sizes=(1,)
                    )
                ),
                types.InputMediaPhoto(media=types.FSInputFile("img/instruction_windows_2.jpg")),
                types.InputMediaPhoto(media=types.FSInputFile("img/instruction_windows_3.jpg")),
                types.InputMediaPhoto(media=types.FSInputFile("img/instruction_windows_4.jpg")),
            ]

            await callback.message.answer_media_group(
                media=media,
            )

            return

        await callback.message.edit_caption(
            caption=text[callback.data.split('_')[-1]].split('|||')[0],
            reply_markup=get_inlineMix_btns(
                btns={"Установить": text[callback.data.split('_')[-1]].split('|||')[1], "Подключиться": 'check_subscription', "⬅ Назад": "install"},
                sizes=(1,)
            )
        )

    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
            return
        raise


# Создание подписки для пользователя после оплаты
@user_private_router.callback_query(F.data.startswith('chooseserver_'))
async def create_subscription(callback: types.CallbackQuery, session, bot):
    payment = await orm_get_payment(session, callback.data.split('_')[-1])
    if payment.paid:
        print('Ошибка: оплата уже совершена')
        return
    
    user = await orm_get_user_by_id(session, payment.user_id)
    tariff = await orm_get_tariff(session, payment.tariff_id)
    servers = await orm_get_servers(session)
    print(user.status) 
    if user.status == 0:
        current_date = datetime.now()
        new_date = current_date + relativedelta(months=tariff.sub_time)

        tun_ids = {}
        user_servers = await orm_get_user_servers(session, user.id)
        if not user_servers:
            for server in servers:
                cookies = await auth(server.server_url, server.login, server.password)
                
                new_vpn_user = await add_customer(
            	    server.server_url,
                	server.indoub_id,
                	cookies, 
                	server.name + '_' + str(user.id),
                	int(new_date.timestamp() * 1000),
            	    tariff.devices,
                   	user.user_id,
                	callback.from_user.username or user.name
                )
                with open("log.txt", "w") as f:
                    f.write(str(new_vpn_user['response']))
                tun_ids[str(server.id)] = new_vpn_user['id']

            if new_vpn_user:
                await orm_end_payment(session, payment.id) 

            await orm_change_user_status(session, user.id, tariff.id, new_date, tun_ids)
        
        elif user_servers:
            new_date = user.sub_end + relativedelta(months=tariff.sub_time)
            date = int(new_date.timestamp() / 1000)

            for user_server in user_servers:
                server = await orm_get_server(session, user_server.server_id)
                cookies = await auth(server.server_url, server.login, server.password)
                
                new_vpn_user = await get_client(
                	cookies, 
            	    server.server_url,
                   	user_server.tun_id,
                	server.indoub_id,
                )
                new_vpn_user = new_vpn_user['response']
                tun_ids[str(server.id)] = new_vpn_user['id']
                await edit_customer_date(server, cookies, date, user_server.tun_id, session)

            if new_vpn_user:
                await orm_end_payment(session, payment.id) 

            await orm_change_user_status(session, user.id, tariff.id, new_date, tun_ids)
 
        data = await get_client(cookies, server.server_url, new_vpn_user['id'], server.indoub_id)
        client_data = data['response']
        settings = data['settings']
        
        await callback.message.delete()
        user = await orm_get_user_by_id(session, payment.user_id)

        url = f"{os.getenv('PAY_PAGE_URL')}/subscription?user_token={callback.from_user.id}"

        await bot.send_message(
            user.user_id, 
            f'<b>✅ Спасибо! Вы оформили подписку!</b>\n\n🗓 Ваша подписка активна до {user.sub_end.date().strftime("%d.%m.%Y")}\n\nСкопируйте ключ доступа. Для копирования ключа нажмите на него 1 раз. ⬇️ \n\n<b>Ваш ключ доступа:</b> \n<code>{url}</code>\n\nДля подключения можете воспользоваться кнопкой ниже ⬇️', 
            reply_markup=get_inlineMix_btns(
                btns={ 
                    "↗️ Подключиться": f'{os.getenv("PAY_PAGE_URL")}/config?user_id={user.id}',
                    "📖Инструкция для подключения": "install_mes",
                    "⚙️ Дополнительная настройка": "https://saturn-online.su/setup-guide/"
                },
                sizes=(1,)
            )
        )

        if user.invited_by:
            from_user = orm_get_user(session, user.invited_by)
            
            days = 15

            if tariff.sub_time == 6:
                days = 30
            elif tariff.sub_time == 12:
                days = 45

            sub_end = from_user.sub_end + relativedelta(days=days)
            servers = await orm_get_user_servers(sesssion, from_user.id) 


            for i in servers:
                server = await orm_get_server(session, i.server_id)
                cookies = await auth(server.server_url, server.login, server.password)

                await edit_customer_date(server, cookies, sub_end, i.tun_id, session)

            await orm_change_user_status(session, from_user.id, from_user.status, sub_end)

            await bot.send_message(
                from_user.user_id, 
                f'<b>Один из приглашеных вами друзей совершил покупку в боте!</b>\n\nВы получаете плюс {days} дней к своей текущей подписке\n\n🗓 Ваша подписка активна до {user.sub_end.date()}\n\n⬇️ Скопируйте ключ доступа. Для копирования ключа нажмите на него 1 раз. ⬇️ \n\n<b>Ваш ключ доступа</b> <code>{url}</code>\n\n<b>Пользователем Windows рекомендуем ознакомиться с <a href="https://saturn-online.su/setup-guide/windows/v2raytun">инструкцией</a></b>\n\n Для подключения можете воспользоваться кнопкой ниже⬇️', 
            )



async def continue_subscription(sub_data: dict, session, user_id, tariff, bot):
    date = sub_data['expire_time'] / 1000 
    date = datetime.fromtimestamp(date)

    await orm_change_user_status(session, user_id=user_id, new_status=tariff.id, tun_id=str(sub_data['id']), sub_end=date)
    url = f"v2raytun://{sub_data['id']}@super.skynetvpn.ru:443?type=tcp&security=tls&fp=chrome&alpn=h3%2Ch2%2Chttp%2F1.1&flow=xtls-rprx-vision#SkynetVPN-{quote(sub_data['email'])}"
    await bot.send_message(user_id, f"<b>Оплата прошла успешно!</b>\nВаша подписка на активна до {date}\n\nВаша ссылка для подключения <code>{url}</code>\n\nСпасибо за покупку! \n\nЕсли у вас есть вопросы, не стесняйтесь задавать.", reply_markup=get_callback_btns(btns={ "⬅ Назад": "back_menu"}))


async def continue_subscription_by_ref(sub_data: dict, session, user_id, tariff, bot):
    date = sub_data['expire_time'] / 1000 
    date = datetime.fromtimestamp(date)

    await orm_change_user_status(session, user_id=user_id, new_status=tariff.id, tun_id=str(sub_data['id']), sub_end=date)
    url = f'v2raytun://{sub_data["id"]}@super.skynetvpn.ru:443?type=tcp&security=tls&fp=chrome&alpn=h3%2Ch2%2Chttp%2F1.1&flow=xtls-rprx-vision#SkynetVPN-{quote(sub_data["email"])}'
    await bot.send_message(user_id, f"<b>Оплата прошла успешно!</b>\nВаша подписка на активна до {date}\n\nВаша ссылка для подключения <code>{url}</code>\n\nСпасибо за покупку! \n\nЕсли у вас есть вопросы, не стесняйтесь задавать.", reply_markup=get_callback_btns(btns={ "⬅ Назад": "back_menu"}))



