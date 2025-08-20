import os

from aiogram.filters import Filter
from aiogram import types

from database.queries import orm_get_blocked_users


class BlockedUsersFilter(Filter):
    async def __call__(self, message, session):
        blocked_users = await orm_get_blocked_users(session=session)
        
        for i in blocked_users:
            if message.from_user.id == i.user_id:
                return False
        
        return True


class OwnerFilter (Filter):
    
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == int(os.getenv('OWNER'))



