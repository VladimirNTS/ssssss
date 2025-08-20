from typing import Union

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import Tariff, User, Admin, FAQ, Payments


# Tariffs
async def orm_get_tariffs(session: AsyncSession):
    '''Возвращает список тарифов
    
    session: Ассинхроная сессия sqlalchemy
    '''
    query = select(Tariff)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_edit_tariff(session: AsyncSession, tariff_id: int, fields: dict):
    """
    Обновляет только переданные поля тарифа по tariff_id.
    fields: dict - только те поля, которые нужно обновить (например: {'name': '...', 'price': 100})
    """
    if not fields:
        return
    query = update(Tariff).where(Tariff.id == tariff_id).values(**fields)
    await session.execute(query)
    await session.commit()


async def orm_add_tariff(session: AsyncSession, data: dict):
    obj = Tariff(
        sub_time=data["sub_time"],
        price=float(data["price"]),
        devices=data["devices"],
        recuring=data["recuring"]
    )
    session.add(obj)
    await session.commit()


async def orm_get_tariff(session: AsyncSession, tariff_id: int):
    query = select(Tariff).where(Tariff.id == tariff_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_delete_tariff(session: AsyncSession, tariff_id: int):
    
    query = delete(Tariff).where(Tariff.id == tariff_id)
    await session.execute(query)
    await session.commit()


# Добавление пользователя
async def orm_add_user(
    session: AsyncSession,
    user_id: int,
    name: Union[str, None] = None,
    sub_id: Union[str, None] = None,
    tun_id: Union[str, None] = None,
    invited_by: Union[int, None] = None,
) -> None:
    '''Добавляет пользователя если его нет
    '''
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    if result.first() is None:
        session.add(
            User(user_id=user_id, name=name, sub_id=sub_id, tun_id=tun_id, status=0, invited_by=invited_by)
        )
        await session.commit()


async def orm_change_user_status(session: AsyncSession, user_id, new_status, sub_end, tun_id):
    
    query = update(User).where(User.id == user_id).values(
            status=new_status,
            sub_end=sub_end,
            tun_id=tun_id
        )
    await session.execute(query)
    await session.commit()


async def orm_get_users(session: AsyncSession):
    '''Возвращает список пользвателей
    
    session: Ассинхроная сессия sqlalchemy
    '''
    query = select(User)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_subscribers(session: AsyncSession):
    '''Возвращает список пользвателей
    
    session: Ассинхроная сессия sqlalchemy
    '''
    query = select(User).where(User.status != 0)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_blocked_users(session: AsyncSession):
    '''Возвращает список пользвателей
    
    session: Ассинхроная сессия sqlalchemy
    '''
    query = select(User).where(User.blocked == True)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_user(session: AsyncSession, user_id: int):
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_get_user_by_id(session: AsyncSession, user_id: int):
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_block_user(session: AsyncSession, user_id: int):
    '''Блокирует пользователя'''
    query = update(User).where(User.id == user_id).values(blocked=True)
    await session.execute(query)
    await session.commit()


async def orm_unblock_user(session: AsyncSession, user_id: int):
    '''Блокирует пользователя'''
    query = update(User).where(User.id == user_id).values(blocked=False)
    await session.execute(query)
    await session.commit()


# Работа с администраторами
async def orm_add_admin(session, user_id):
    '''Добавить нового администратора в таблицу'''
    session.add(
        Admin(
            user_id=user_id
        )
    )
    await session.commit()


async def orm_delete_admin(session, user_id):
    '''Удалить администратора из таблицы'''
    query = delete(Admin).where(user_id==user_id)
    await session.execute(query)
    await session.commit()


# FAQ
async def orm_get_faq(session: AsyncSession):
    '''Возвращает список вопросов и ответов'''
    query = select(FAQ)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_add_faq(session: AsyncSession, data: dict):
    '''Добавляет вопрос и ответ в таблицу'''
    obj = FAQ(
        ask=data["ask"],
        answer=data["answer"],
    )
    session.add(obj)
    await session.commit()


async def orm_get_faq_by_id(session: AsyncSession, id: int):
    '''Возвращает вопрос и ответ по id'''
    query = select(FAQ).where(FAQ.id == id)
    result = await session.execute(query)
    return result.scalar()


async def orm_delete_faq(session: AsyncSession, id: int):
    '''Удалить вопрос из таблицы'''
    query = delete(FAQ).where(FAQ.id == id)
    await session.execute(query)
    await session.commit()


async def orm_edit_faq(session: AsyncSession, id: int, fields: dict):
    '''Обновляет только переданные поля вопроса и ответа по id.
    fields: dict - только те поля, которые нужно обновить (например: {'ask': '...', 'answer': '...'})
    '''
    if not fields:
        return
    query = update(FAQ).where(FAQ.id == id).values(**fields)
    await session.execute(query)
    await session.commit()


async def orm_new_payment(session: AsyncSession, user_id: int, tariff_id: int):
    '''Создает новую запись о платеже в таблицу'''
    obj = Payments(
        user_id=user_id,
        tariff_id=tariff_id,
    )
    session.add(obj)
    await session.commit()


async def orm_get_payment(session: AsyncSession, payment_id):
    '''Возвращает запись о платеже по id'''
    query = select(Payments).where(Payments.id == payment_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_get_last_payment_id(session: AsyncSession):
    '''Возвращает последнюю запись о платеже'''
    query = select(Payments).order_by(Payments.id.desc()).limit(1)
    result = await session.execute(query)
    payment = result.scalar_one_or_none()
    
    return payment.id if payment else 0