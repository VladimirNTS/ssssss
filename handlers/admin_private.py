from datetime import datetime

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from kbds.inline import get_callback_btns
from filters.users_filter import OwnerFilter
from skynetapi.skynetapi import edit_customer_date, auth, get_client, edit_customer_limit_ip
from database.queries import (
    orm_get_user_by_id,
    orm_get_users,
    orm_get_subscribers,
    orm_block_user,
    orm_get_tariffs,
    orm_add_tariff,
    orm_delete_tariff,
    orm_get_tariff,
    orm_edit_tariff,
    orm_add_faq,
    orm_get_faq,
    orm_delete_faq,
    orm_edit_faq,
    orm_unblock_user,
    orm_add_server,
    orm_edit_server,
    orm_get_servers,
    orm_get_server,
    orm_get_user_servers,
    orm_change_user_status,
)

admin_private_router = Router()
admin_private_router.message.filter(OwnerFilter())



@admin_private_router.callback_query(F.data == "admin")
async def start(callback):
        await callback.message.answer("Здраствуйте, чем займемся сегодня?", reply_markup=get_callback_btns(btns={
        '📃 Управление тарифами': 'tariffs_list',
        '📃 Список заказов': 'orders_list',
        '📫 Рассылка': 'send',
        '⚙ Редактировать FAQ': 'edit_faq',
        '⚙ Управление серверами': 'servers_list'
    }, sizes=(2,2,1)))


@admin_private_router.message(Command("admin"))
async def start(message: types.Message):
	await message.answer("Здраствуйте, чем займемся сегодня?", reply_markup=get_callback_btns(btns={
        '📃 Управление тарифами': 'tariffs_list',
        '📃 Список заказов': 'orders_list',
        '📫 Рассылка': 'send',
        '⚙ Редактировать FAQ': 'edit_faq',
        '⚙ Управление серверами': 'servers_list'
    }, sizes=(2,2,1)))
	

# Получить список тарифов
@admin_private_router.callback_query(F.data == 'tariffs_list')
async def choose_category(callback_query: types.CallbackQuery, session):
    await callback_query.answer()
    

    tariff_list = await orm_get_tariffs(session)

    for tariff in tariff_list:
        await callback_query.message.answer(
            text=f"<b>Срок:</b> {tariff.sub_time} месяцев\n<b>Цена:</b> {tariff.price}\n<b>Количество устройств:</b> {tariff.devices}\n<b>Тип: {'повторяющийся платеж' if tariff.recuring else 'единоразовый платеж'}</b>", 
            reply_markup=get_callback_btns(btns={'Изменить': f'edittariff_{tariff.id}', 'Удалить': f'deletetariff_{tariff.id}'})
        )
    
    if tariff_list:
        await callback_query.message.answer(
                text="Вот список тарифов ⬆", 
                reply_markup=get_callback_btns(btns={'Добавить новый тариф': f'addtariff', 'Добавить единоразовый платеж': f'addonepay'})
            )
    else:
        await callback_query.message.answer(
                text="Тарифов пока нет", 
                reply_markup=get_callback_btns(btns={'Добавить новый тариф': f'addtariff', 'Добавить единоразовый платеж': f'addonepay'})
            )


# FSM для добавления тарифов
class FSMAddTariff(StatesGroup):
    sub_time = State()
    price = State()
    devices = State()

# Undo text for add tariff FSM
FSMAddTariff_undo_text = {
    'FSMAddTariff:sub_time': 'Введите время подписки (в днях) заново',
    'FSMAddTariff:price': 'Введите цену подписки заново',
}

# Cancel handler for FSMAddTariff
@admin_private_router.message(StateFilter("*"), F.text.in_({'/отмена', 'отмена'}))
async def cancel_fsm_add_tariff(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer('❌ Отменено')

# Back handler for FSMAddTariff
@admin_private_router.message(StateFilter('FSMAddTariff'), F.text.in_({'/назад', 'назад'}))
async def back_step_add_tariff(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == FSMAddTariff.name.state:
        await message.answer('Предыдущего шага нет, введите название тарифа или напишите "отмена"')
        return
    previous = None
    for step in FSMAddTariff.all_states:
        if step.state == current_state:
            if previous is not None:
                await state.set_state(previous.state)
                await message.answer(f"Ок, вы вернулись к прошлому шагу. {FSMAddTariff_undo_text[previous.state]}")
            return
        previous = step


@admin_private_router.callback_query(StateFilter(None), F.data == "addtariff")
async def add_product_description(callback: types.CallbackQuery, state: FSMContext):
    
    await callback.message.answer('Введите время подписки (в месяцах):')
    await state.set_state(FSMAddTariff.sub_time)


@admin_private_router.message(FSMAddTariff.sub_time)
async def add_product_description(message, state: FSMContext):
    try:
        await state.update_data(sub_time=int(message.text))
    except:
         await message.answer('Неверный формат. Введите время подписки (в месяцах) еще раз:')
         return
    await message.answer('Введите количество устройств:')
    await state.set_state(FSMAddTariff.devices)


@admin_private_router.message(FSMAddTariff.devices)
async def add_product_description(message: types.Message, state: FSMContext):
    try:
        await state.update_data(devices=int(message.text))
    except:
         await message.answer('Неверный формат. Введите время подписки (в месяцах) еще раз:')
         return
    await message.answer('Введите цену подписки:')
    await state.set_state(FSMAddTariff.price)
    


@admin_private_router.message(FSMAddTariff.price)
async def add_product(message: types.Message, state: FSMContext, session):
    try:
        await state.update_data(price=int(message.text))
        await state.update_data(recuring=True)
    except:
         await message.answer('Неверный формат. Введите цену еще раз:')
         return
    await message.answer('✅ Тариф добавлен')
    data = await state.get_data()
    await orm_add_tariff(session=session, data=data)
    await state.clear()
    


# Удаление тарифа
@admin_private_router.callback_query(F.data.startswith('deletetariff_'))
async def delete_product(callback_query: types.CallbackQuery, session):
    await callback_query.answer()
    await orm_delete_tariff(session, callback_query.data.split('_')[-1])
    await callback_query.message.answer("✅ Тариф удален")
    await callback_query.message.delete()


class FSMEditTariff(StatesGroup):
    sub_time = State()
    price = State()
    devices = State()


@admin_private_router.callback_query(StateFilter(None), F.data.startswith("edittariff"))
async def add_product(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(tariff_id=callback.data.split('_')[-1])
    await callback.message.answer('Введите новое время подписки (в месяцах) (или . чтобы пропустить):')
    await state.set_state(FSMEditTariff.sub_time)

@admin_private_router.message(FSMEditTariff.sub_time)
async def edit_tariff_sub_time(message: types.Message, state: FSMContext):
    if message.text == '.':
        await state.update_data(sub_time=None)
        await message.answer('Введите новую цену подписки (или . чтобы пропустить):')
        await state.set_state(FSMEditTariff.price)
        return
    try:
        await state.update_data(sub_time=int(message.text))
        await message.answer('Введите новую цену подписки (или . чтобы пропустить):')
        await state.set_state(FSMEditTariff.price)
    except:
        await message.answer('Неверный формат. Введите время подписки (в месяцах) еще раз:')

@admin_private_router.message(FSMEditTariff.price)
async def edit_tariff_price(message: types.Message, state: FSMContext):
    if message.text == '.':
        await state.update_data(price=None)
        await message.answer('Введите новое количество устройств (или . чтобы пропустить):')
        await state.set_state(FSMEditTariff.devices)
        return
    try:
        await state.update_data(price=int(message.text))
        await message.answer('Введите новое количество устройств (или . чтобы пропустить):')
        await state.set_state(FSMEditTariff.devices)
    except:
        await message.answer('Неверный формат. Введите цену еще раз:')

    

@admin_private_router.message(FSMEditTariff.devices)
async def edit_tariff_pay_id(message: types.Message, state: FSMContext, session):
    if message.text == '.':
        await state.update_data(devices=None)
    else:
        await state.update_data(devices=message.text.split('=')[-1])
    data = await state.get_data()
    # Оставляем только те поля, которые не None
    update_fields = {k: v for k, v in data.items() if v is not None}
    del update_fields['tariff_id']
    await message.answer('✅ Тариф изменен')
    await orm_edit_tariff(session=session, tariff_id=data['tariff_id'], fields=update_fields)
    await state.clear()


# FSM для добавления единоразового платежа
class FSMAddOnePay(StatesGroup):
    sub_time = State()
    price = State()
    devices = State()

# Undo text for add tariff FSM
FSMAddOnePay_undo_text = {
    'FSMAddTariff:sub_time': 'Введите время платежа (в днях) заново',
    'FSMAddTariff:price': 'Введите цену платежа заново',
}

# Cancel handler for FSMAddTariff
@admin_private_router.message(StateFilter("*"), F.text.in_({'/отмена', 'отмена'}))
async def cancel_fsm_add_tariff(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer('❌ Добавление платежа отменено')

# Back handler for FSMAddTariff
@admin_private_router.message(StateFilter('FSMAddOnePay'), F.text.in_({'/назад', 'назад'}))
async def back_step_add_tariff(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == FSMAddOnePay.name.state:
        await message.answer('Предыдущего шага нет, введите название платежа или напишите "отмена"')
        return
    previous = None
    for step in FSMAddOnePay.all_states:
        if step.state == current_state:
            if previous is not None:
                await state.set_state(previous.state)
                await message.answer(f"Ок, вы вернулись к прошлому шагу. {FSMAddOnePay_undo_text[previous.state]}")
            return
        previous = step


@admin_private_router.callback_query(StateFilter(None), F.data == "addonepay")
async def add_product(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer('Введите время подписки (в днях):')
    await state.set_state(FSMAddOnePay.sub_time)


@admin_private_router.message(FSMAddOnePay.sub_time)
async def add_product_description(message, state: FSMContext):
    try:
        await state.update_data(sub_time=int(message.text))
    except:
         await message.answer('Неверный формат. Введите время подписки (в месяцах) еще раз:')
         return
    await message.answer('Введите количество устройств:')
    await state.set_state(FSMAddOnePay.devices)


@admin_private_router.message(FSMAddOnePay.devices)
async def add_product_description(message: types.Message, state: FSMContext):
    try:
        await state.update_data(devices=int(message.text))
    except:
        await message.answer('Неверный формат. Введите время подписки (в днях) еще раз:')
        return
    await message.answer('Введите цену платежа:')
    await state.set_state(FSMAddOnePay.price)
    



@admin_private_router.message(FSMAddOnePay.price)
async def add_product(message: types.Message, state: FSMContext, session):
    try:
        await state.update_data(price=int(message.text))
    except:
         await message.answer('Неверный формат. Введите цену еще раз:')
    await state.update_data(pay_id=message.text.split('=')[-1])
    await state.update_data(recuring=False)
    data = await state.get_data()
    try:
        await orm_add_tariff(session=session, data=data)
        await message.answer('✅ Тариф добавлен')
    except:
        await message.answer('❌ Ошибка добавления тарифа')
    finally:
        await state.clear()
    


# FAQ
@admin_private_router.callback_query(F.data == 'edit_faq')
async def edit_faq(callback: types.CallbackQuery, state: FSMContext, session):
    
    await callback.answer()
    faq_list = await orm_get_faq(session)
    for faq in faq_list:
        await callback.message.answer(
            text=f"<b>Вопрос:</b> {faq.ask}\n<b>Ответ:</b> {faq.answer}",
            reply_markup=get_callback_btns(btns={'Изменить': f'editfaq_{faq.id}', 'Удалить': f'deletefaq_{faq.id}'})
        )
    if faq_list:
        await callback.message.answer(
                text="Вот список вопросов ⬆",
                reply_markup=get_callback_btns(btns={'Добавить новый вопрос': f'addfaq'})
            )
    else:
        await callback.message.answer(
                text="Вопросов пока нет",
                reply_markup=get_callback_btns(btns={'Добавить новый вопрос': f'addfaq'})
            )


# FSM для добавления вопросов
class FSMAddFAQ(StatesGroup):
    ask = State()
    answer = State()


@admin_private_router.callback_query(StateFilter(None), F.data == "addfaq")
async def add_faq(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Введите вопрос:')
    await state.set_state(FSMAddFAQ.ask)


@admin_private_router.message(FSMAddFAQ.ask)
async def add_faq_description(message: types.Message, state: FSMContext):
    await state.update_data(ask=message.text)
    await message.answer('Введите ответ:')
    await state.set_state(FSMAddFAQ.answer)


@admin_private_router.message(FSMAddFAQ.answer)
async def add_faq_description(message: types.Message, state: FSMContext, session):
    await state.update_data(answer=message.text)
    await message.answer('✅ Вопрос добавлен')
    data = await state.get_data()
    await orm_add_faq(session=session, data=data)
    await state.clear()


# FSM изменения вопросов
class FSMEditFAQ(StatesGroup):
    id = State()
    ask = State()
    answer = State()


@admin_private_router.callback_query(StateFilter(None), F.data.startswith("editfaq"))
async def edit_faq(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(faq_id=callback.data.split('_')[-1])
    await callback.answer()
    await callback.message.answer('Вы редактируете вопрос. Для отмены напишите /отмена или /назад')
    await callback.message.answer('Введите новый вопрос, для пропуска напишите ".":')
    await state.set_state(FSMEditFAQ.ask)


@admin_private_router.message(FSMEditFAQ.ask)
async def edit_faq_name(message: types.Message, state: FSMContext):
    if message.text == '.':
        await state.update_data(ask=None)
    else:
        await state.update_data(ask=message.text)
    await message.answer('Введите новый ответ, для пропуска напишите ".":')
    await state.set_state(FSMEditFAQ.answer)


@admin_private_router.message(FSMEditFAQ.answer)
async def edit_faq_description(message: types.Message, state: FSMContext, session):
    if message.text == '.':
        await state.update_data(answer=None)
    else:
        await state.update_data(answer=message.text)
    data = await state.get_data()
    # Оставляем только те поля, которые не None
    update_fields = {k: v for k, v in data.items() if v is not None}
    del update_fields['faq_id']
    await message.answer('✅ Вопрос изменен')
    await orm_edit_faq(session=session, id=data['faq_id'], fields=update_fields)
    await state.clear()


# Удаление вопроса
@admin_private_router.callback_query(F.data.startswith('deletefaq_'))
async def delete_faq(callback_query: types.CallbackQuery, session):
    await callback_query.answer()
    await orm_delete_faq(session, callback_query.data.split('_')[-1])
    await callback_query.message.answer("✅ Вопрос удален")
    await callback_query.message.delete()


class FSMSendMessages(StatesGroup):
    message = State()
    picture = State()
    recipients = State()


@admin_private_router.callback_query(StateFilter(None), F.data == "send")
async def send_messages(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Введите сообщение для отправки:')
    await state.set_state(FSMSendMessages.message)


@admin_private_router.message(FSMSendMessages.message)
async def send_messages_description(message: types.Message, state: FSMContext):
    await state.update_data(message=message.text)
    await message.answer('Отправте картинку если нужна. Если не нужна то отправте ".":')
    await state.set_state(FSMSendMessages.picture)


@admin_private_router.message(FSMSendMessages.picture, or_f(F.photo, F.text))
async def send_messages_picture(message: types.Message, state: FSMContext):
    if message.text == '.':
        await message.answer('Выберите кому отправить сообщение: активные подписчики или все (включая гостей).', reply_markup=get_callback_btns(btns={'Активные подписчики': 'active_subscribers', 'Все': 'all'}))
        await state.set_state(FSMSendMessages.recipients)
    else:
        await state.update_data(picture=message.photo[0].file_id)
        await message.answer('Выберите кому отправить сообщение: активные подписчики или все (включая гостей).', reply_markup=get_callback_btns(btns={'Активные подписчики': 'active_subscribers', 'Все': 'all'}))
        await state.set_state(FSMSendMessages.recipients)


@admin_private_router.callback_query(FSMSendMessages.recipients, F.data == "active_subscribers")
async def send_messages_active_subscribers(callback: types.CallbackQuery, state: FSMContext, session, bot):
    await callback.answer()
    users = await orm_get_subscribers(session)
    for user in users:
        data = await state.get_data()

        if data.get('picture'):
            await bot.send_photo(chat_id=user.user_id, photo=data['picture'], caption=data['message'])
        else:
            await bot.send_message(chat_id=user.user_id, text=data['message'])
        
    
    await callback.message.answer(f"Сообщение отправленно {len(users)} пользователям")
    await state.clear()


@admin_private_router.callback_query(FSMSendMessages.recipients, F.data == "all")
async def send_messages_active_subscribers(callback: types.CallbackQuery, state: FSMContext, session, bot):
    await callback.answer()
    users = await orm_get_users(session)
    for user in users:
        data = await state.get_data()
        if data.get('picture'):
            await bot.send_photo(chat_id=user.user_id, photo=data['picture'], caption=data['message'])
        else:
            await bot.send_message(chat_id=user.user_id, text=data['message'])
    
    await callback.message.answer(f"Сообщение отправленно {len(users)} пользователям")
    await state.clear()


# Заказы 
@admin_private_router.callback_query(StateFilter(None), F.data == "orders_list")
async def orders_list(callback: types.CallbackQuery, session):
    await callback.answer()
    message_text = ""
    orders = await orm_get_users(session)
    for order in orders:
        tariff = await orm_get_tariff(session, order.status)
        servers = await orm_get_user_servers(session, order.id)
        if order.status > 0:
            server = await orm_get_server(session, servers[0].server_id)
            cookies = await auth(server.server_url, server.login, server.password)
            with open('log.txt', 'w') as f:
                f.write(str(servers[0].tun_id))
 
            client = await get_client(cookies, server.server_url, servers[0].tun_id, server.indoub_id)
            message_text = f"<b>ID:</b> {order.user_id}\n<b>Имя:</b> {order.name}\n<b>Тариф:</b> {tariff.price} за {tariff.sub_time} мес.\nДата окончания: {order.sub_end.strftime('%d.%m.%Y')}\nКоличество устройств: {client['response']['limitIp']}"
    
            await callback.message.answer(
                text=message_text,
                reply_markup=get_callback_btns(
                    btns={
                        'Заблокировать пользователя': f'blockuser_{order.user_id}',
                        'Изменить дату окончания': f"renew_{order.id}",
                        'Изменить количество устройств': f"redevice_{order.id}",
                    }, sizes=[1,])
                )

    if orders:
        await callback.message.answer(
                text=f"Вот список заказов ⬆ \n\nВсего подписчиков: {len(orders)}",
            )
    else:
        await callback.message.answer(
                text=f"Заказов пока нет\n\nВсего подписчиков: {len(orders)}",
            )


class FSMRenew(StatesGroup):
    days = State()

@admin_private_router.callback_query(StateFilter(None), F.data.startswith('renew_'))
async def renew_sub(callback, state):
    await state.update_data(user_id=callback.data.split())
    await callback.message.answer("Введите новую дату в формате дд.мм.гггг:")
    await state.set_state(FSMRenew.days)


@admin_private_router.message(FSMRenew.days)
async def days(message, session, state):
    data = await state.get_data()
    now = datetime.now()
    user_id = data['user_id'][0].split('_')[-1]
    date = message.text.split('.')
    if len(date) != 3:
        await message.answer("Неверный формат. Введите новую дату в формате дд.мм.гггг:")
        return
    
    user = await orm_get_user_by_id(session, user_id)
    servers = await orm_get_user_servers(session, user.id)
    
    new_date = datetime(int(date[2]), int(date[1]), int(date[0]), now.hour, now.minute, now.second, now.microsecond)
    new_unix_date = int(new_date.timestamp() * 1000) 
    print(new_date, new_unix_date)
    for server in servers:
        server_info = await orm_get_server(session, server.server_id)
        cookies = await auth(server_info.server_url, server_info.login, server_info.password)
        await edit_customer_date(server_info, cookies, new_unix_date, server.tun_id, session)
    
    await orm_change_user_status(session, user_id, user.status, new_date)
    
    await message.answer("✅ Дата изменена")
    await state.clear()


class FSMDevice(StatesGroup):
    devices = State()

@admin_private_router.callback_query(StateFilter(None), F.data.startswith('redevice_'))
async def renew_sub(callback, state):
    await state.update_data(user_id=callback.data.split())
    await callback.message.answer("Введите новое количество устройств")
    await state.set_state(FSMDevice.devices)


@admin_private_router.message(FSMDevice.devices)
async def days(message, session, state):
    data = await state.get_data()
    user_id = data['user_id'][0].split('_')[-1]
    try:
        date = int(message.text)
        user = await orm_get_user_by_id(session, user_id)
        servers = await orm_get_user_servers(session, user.id)
        
        for server in servers:
            server_info = await orm_get_server(session, server.server_id)
            cookies = await auth(server_info.server_url, server_info.login, server_info.password)
            cust = await edit_customer_limit_ip(server_info, cookies, date, user.user_id, session, server.tun_id)
            print(cust)
    
        await message.answer("✅ Количество устройств изменено.")
        await state.clear()


    except:
        await message.answer("Неверный формат. Введите новое количество устройств")
        return
    
    

# заблокировать пользователя
@admin_private_router.callback_query(StateFilter(None), F.data.startswith('blockuser_'))
async def block_user(callback: types.CallbackQuery, session):
    await callback.answer()
    await orm_block_user(session, callback.data.split('_')[-1])
    await callback.message.answer("✅ Пользователь заблокирован", reply_markup=get_callback_btns(btns={'разблокировать пользователя': f"unblockuser_{callback.data.split('_')[-1]}"}))


# Разблокировать пользователя
@admin_private_router.callback_query(StateFilter(None), F.data.startswith('unblockuser_'))
async def unblock_user(callback: types.CallbackQuery, session):
    await callback.answer()
    await orm_unblock_user(session, callback.data.split('_')[-1])
    await callback.message.answer("✅ Пользователь разблокирован")




# Получить список серверов
@admin_private_router.callback_query(F.data == 'servers_list')
async def choose_category(callback_query: types.CallbackQuery, session):
    await callback_query.answer()
    

    servers_list = await orm_get_servers(session)

    for server in servers_list:
        await callback_query.message.answer(
            text=f"<b>Имя:</b> {server.name}\n<b>url:</b> {server.server_url}\n<b>Логин:</b> {server.login}\n<b>Пароль: {server.password}</b>", 
            reply_markup=get_callback_btns(btns={'Изменить': f'editserver_{server.id}', 'Удалить': f'deleteserver_{server.id}'})
        )
    
    if servers_list:
        await callback_query.message.answer(
                text="Вот список серверов ⬆", 
                reply_markup=get_callback_btns(btns={'Добавить новый сервер': f'addserver'})
            )
    else:
        await callback_query.message.answer(
                text="Серверов пока нет", 
                reply_markup=get_callback_btns(btns={'Добавить новый сервер': f'addserver'})
            )


# FSM для добавления тарифов
class FSMAddServer(StatesGroup):
    name = State()
    url = State()
    login = State()
    password = State()
    indoub_id = State()

# Undo text for add tariff FSM
FSMAddTariff_undo_text = {
    'FSMAddServer:name': 'Введите имя сервера заново',
    'FSMAddServer:url': 'Введите url на админ панель сервера заново',
    'FSMAddServer:login': 'Введите логин админ панели сервера заново',
    'FSMAddServer:password': 'Введите пароль админ панели сервера заново',
}


# Back handler for FSMAddTariff
@admin_private_router.message(StateFilter('FSMAddServer'), F.text.in_({'/назад', 'назад'}))
async def back_step_add_tariff(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == FSMAddTariff.name.state:
        await message.answer('Предыдущего шага нет, введите название тарифа или напишите "отмена"')
        return
    previous = None
    for step in FSMAddTariff.all_states:
        if step.state == current_state:
            if previous is not None:
                await state.set_state(previous.state)
                await message.answer(f"Ок, вы вернулись к прошлому шагу. {FSMAddTariff_undo_text[previous.state]}")
            return
        previous = step


@admin_private_router.callback_query(StateFilter(None), F.data == "addserver")
async def add_product_description(callback: types.CallbackQuery, state: FSMContext):
    
    await callback.message.answer('Введите имя сервера (оно будет отображаться пользователя при выборе сервера):')
    await state.set_state(FSMAddServer.name)


@admin_private_router.message(FSMAddServer.name)
async def add_product_description(message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('Введите url на админ панель сервера:')
    await state.set_state(FSMAddServer.url)


@admin_private_router.message(FSMAddServer.url)
async def add_product_description(message: types.Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer('Введите ID индауба:')
    
    await state.set_state(FSMAddServer.indoub_id)
    

@admin_private_router.message(FSMAddServer.indoub_id)
async def add_product_description(message: types.Message, state: FSMContext):
    try:
        await state.update_data(indoub_id=int(message.text))
        await message.answer('Введите логин админ панели сервера:')
    
        await state.set_state(FSMAddServer.login)
    except:
        await message.answer('Неверный формат, введите id индауба:')


@admin_private_router.message(FSMAddServer.login)
async def add_product_description(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text)
    await message.answer('Введите пароль админ панели сервера:')

    await state.set_state(FSMAddServer.password)


@admin_private_router.message(FSMAddServer.password)
async def add_product(message: types.Message, state: FSMContext, session):
    await state.update_data(password=message.text)
    await message.answer('✅ Сервер добавлен')
    data = await state.get_data()
    await orm_add_server(session=session, data=data)
    await state.clear()


async def add_users_to_new_server(session, server_id):
    new_server = await orm_get_server(session, server_id)
    users = await orm_get_users(session)



# Удаление сервера из базы
@admin_private_router.callback_query(F.data.startswith('deleteserver_'))
async def delete_product(callback_query: types.CallbackQuery, session):
    await callback_query.answer()
    await orm_delete_server(session, callback_query.data.split('_')[-1])
    await callback_query.message.answer("✅ Сервер удален")
    await callback_query.message.delete()


class FSMEditServer(StatesGroup):
    name = State()
    url = State()
    login = State()
    password = State()
    indoub_id = State()

FSMAddTariff_undo_text = {
    'FSMEditServer:name': 'Введите имя сервера заново',
    'FSMEditServer:url': 'Введите url на админ панель сервера заново',
    'FSMEditServer:login': 'Введите логин админ панели сервера заново',
    'FSMEditServer:password': 'Введите пароль админ панели сервера заново',
}


@admin_private_router.message(StateFilter('FSMEditServer'), F.text.in_({'/назад', 'назад'}))
async def back_step_add_tariff(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == FSMEditServer.name.state:
        await message.answer('Предыдущего шага нет, введите название тарифа или напишите "отмена"')
        return
    previous = None
    for step in FSMEditServer.all_states:
        if step.state == current_state:
            if previous is not None:
                await state.set_state(previous.state)
                await message.answer(f"Ок, вы вернулись к прошлому шагу. {FSMAddTariff_undo_text[previous.state]}")
            return
        previous = step


@admin_private_router.callback_query(StateFilter(None), F.data.startswith("editserver"))
async def add_product_description(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(server_id=callback.data.split('_')[-1])
    
    await callback.message.answer('Введите имя сервера (оно будет отображаться пользователя при выборе сервера) (или . чтобы пропустить):')
    await state.set_state(FSMEditServer.name)


@admin_private_router.message(FSMEditServer.name)
async def add_product_description(message, state: FSMContext):
    if message.text == '.':
        await state.update_data(name=None)
    else:
        await state.update_data(name=message.text)
    await message.answer('Введите url на админ панель сервера (или . чтобы пропустить):')
    await state.set_state(FSMEditServer.url)


@admin_private_router.message(FSMEditServer.url)
async def add_product_description(message: types.Message, state: FSMContext):
    if message.text == '.':
        await state.update_data(server_url=None)
    else:
        await state.update_data(server_url=message.text)
    await message.answer('Введите id индауба (или . чтобы пропустить):')
    
    await state.set_state(FSMEditServer.indoub_id)
    

@admin_private_router.message(FSMEditServer.indoub_id)
async def add_product_description(message: types.Message, state: FSMContext):
    try:
        if message.text == '.':
            await state.update_data(password=None)
        else:
            await state.update_data(indoub_id=int(message.text))
        await message.answer('Введите логин админ панели сервера (или . чтобы пропустить):')
    
        await state.set_state(FSMEditServer.login)
    except:
        await message.answer('Неверный формат, введите id индауба:')


@admin_private_router.message(FSMEditServer.login)
async def add_product_description(message: types.Message, state: FSMContext):
    if message.text == '.':
        await state.update_data(password=None)
    else:
        await state.update_data(login=message.text)
    await message.answer('Введите пароль админ панели сервера (или . чтобы пропустить):')

    await state.set_state(FSMEditServer.password)

    

@admin_private_router.message(FSMEditServer.password)
async def edit_tariff_pay_id(message: types.Message, state: FSMContext, session):
    if message.text == '.':
        await state.update_data(password=None)
    else:
        await state.update_data(password=message.text)
    data = await state.get_data()
    # Оставляем только те поля, которые не None
    update_fields = {k: v for k, v in data.items() if v is not None}
    del update_fields['server_id']
    await message.answer('✅ Сервер изменен')
    await orm_edit_server(session=session, id=data['server_id'], fields=update_fields)
    await state.clear()


