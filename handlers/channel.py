from aiogram import Router, F
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.enums import ChatMemberStatus
from database import get_admins
import logging
router = Router()

ADMIN_IDS = get_admins()  # Список админов бота


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=True))
async def bot_added_to_chat(event: ChatMemberUpdated):
    logging.info(f"Получено обновление: {event}")
    if event.new_chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
        chat = event.chat
        chat_type = "канал" if chat.type == "channel" else "группа"

        # Отправляем уведомление админам
        for admin_id in ADMIN_IDS:
            await event.bot.send_message(
                admin_id,
                f"📢 Бот был добавлен в {chat_type}: {chat.title} (@{chat.username if chat.username else 'без юзернейма'})"
            )

@router.my_chat_member()
async def bot_status_change(event: ChatMemberUpdated):
    logging.info(f"Получено обновление: {event}")
    # Выведем старый и новый статус для наглядности
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    logging.info(f"Старый статус: {old_status}, Новый статус: {new_status}")

    # Если нужно, можем добавить условие
    if new_status in ["member", "administrator"] and old_status != new_status:
        chat = event.chat
        chat_type = "канал" if chat.type == "channel" else "группа"
        for admin_id in ADMIN_IDS:
            await event.bot.send_message(
                admin_id,
                f"📢 Бот был добавлен в {chat_type}: {chat.title} (@{chat.username if chat.username else 'без юзернейма'})"
            )