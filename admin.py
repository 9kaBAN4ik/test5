# admin.py
import re
import sqlite3
from aiogram import Router, F, types
from aiogram.types import Message, ContentType,ReplyKeyboardRemove,InputFile,BufferedInputFile,InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter,Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID  # Главный администратор из config
from aiogram.utils.markdown import hbold
from database import (set_user_role, get_user_role,get_user_courses, get_user_products,
                        add_aphorism,add_image,get_rate, update_rate,update_product_status,get_pending_products,
                      get_users_by_tag,get_all_tags,get_current_rewards,update_reward,get_all_products_two,
                      get_users_by_product,get_user_balance,get_all_products,get_product_by_id,get_partners_with_status,
                      get_partner_by_id_admin,update_partner_status,get_partner_by_id,get_feedbacks,update_user_role_for_partner,
                      get_user_by_id_admin,get_all_aphorisms,aphorism_exists,delete_aphorism,update_aphorism_text,update_aphorism_author,save_referral_system,
                      get_all_users,add_balance_to_user,connect_db,load_texts,get_user_language,get_current_referral_system,update_referral_rewards,create_referral_system,get_users_with_balance,add_referral_reward,get_referral_reward,get_referral_system_id,get_username_by_user_id_for_admin,
                      get_user_id_for_ticket,get_admins,get_ved_exchange_rate)# Работа с ролями пользователей
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton,InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from math import ceil
import logging
import random
import math
import os
from handlers.add_product_handler import cancel_process
from handlers.balance_handler import get_exchange_rates
router = Router()
ITEMS_PER_PAGE = 5
# Состояния для добавления афоризма
class AddAphorism(StatesGroup):
    waiting_for_text = State()
    waiting_for_author = State()
# Состояния для загрузки фото афоризма
class AphorismStates(StatesGroup):
    waiting_for_image = State()
# Определяем состояния для FSM
class AddPartnerState(StatesGroup):
    waiting_for_user_id = State()
class ProductMessageState(StatesGroup):
    waiting_for_message = State()
class ReferralEditState(StatesGroup):
    waiting_for_new_reward = State()
class AddAdminState(StatesGroup):
    waiting_for_user_id = State()
class RateUpdateState(StatesGroup):
    waiting_for_rate = State()
class BroadcastState(StatesGroup):
    waiting_for_message_admin = State()
class DeleteAphorism(StatesGroup):
    waiting_for_id = State()
class EditAphorism(StatesGroup):
    waiting_for_id = State()
    waiting_for_choice = State()
    waiting_for_new_text = State()
    waiting_for_new_author = State()
class AddBalanceStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()
class LotteryStates(StatesGroup):
    waiting_for_price = State()
class FileUpdateState(StatesGroup):
    waiting_for_file = State()
class BroadcastStateForAdminAllUsers(StatesGroup):
    waiting_for_message = State()




texts = load_texts('texts.xlsx')
FILE_PATH = 'texts.xlsx'
@router.message(lambda message: message.text and message.text.strip() in {str(texts['admin_panel_button'].get(lang, '') or '').strip() for lang in texts['admin_panel_button']})
async def admin_menu(message: Message):
    user_role = await get_user_role(message.from_user.id)
    user_id = message.from_user.id
    user_language = await get_user_language(user_id)

    if user_role != 'admin':
        await message.answer(
            "У вас нет доступа к админ-панели.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=texts['back_to_main_menu_button'][user_language])]],
                resize_keyboard=True
            )
        )
        return

    # Основное меню с подразделами
    buttons = [
        [KeyboardButton(text=texts["admin_with_user"][user_language]),
         KeyboardButton(text=texts["admin_products_moves"][user_language])],
        [KeyboardButton(text=texts["admin_aphorisms_move"][user_language]),
         KeyboardButton(text=texts["admin_currency"][user_language])],
        [KeyboardButton(text=texts["admin_broadcasts"][user_language]),
         KeyboardButton(text=texts["admin_applications"][user_language])],
        [KeyboardButton(text=texts["admin_commands"][user_language]),
        KeyboardButton(text=texts["admin_referral_system"][user_language])],
        [KeyboardButton(text=texts["admin_lottery"][user_language])],
        [KeyboardButton(text=texts["back_to_main_menu_button"][user_language])]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer("Выберите категорию:", reply_markup=keyboard)


# Фильтр для обработки меню админа
class AdminMenuFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        user_language = await get_user_language(message.from_user.id)
        return message.text in [texts[key][user_language] for key in [
            "admin_with_user",
            "admin_products_moves",
            "admin_aphorisms_move",
            "admin_currency",
            "admin_broadcasts",
            "admin_applications",
            "admin_commands",
            "admin_referral_system",
            "admin_lottery",
        ]]

@router.message(AdminMenuFilter())
async def admin_submenu(message: Message):
    user_language = await get_user_language(message.from_user.id)
    category = message.text

    submenus = {
        texts["admin_with_user"][user_language]: [
            texts["view_all_users"][user_language],
            texts["add_balance_to_user"][user_language],
            texts["add_admin_button"][user_language],
            texts["add_partner_button_admin"][user_language],
            texts["view_query_results"][user_language],
            texts["view_users_with_balance"][user_language],
        ],
        texts["admin_products_moves"][user_language]: [
            texts["view_all_products"][user_language],
            texts["show_pending_products"][user_language],
        ],
        texts["admin_aphorisms_move"][user_language]: [
            texts["add_aforism"][user_language],
            texts["add_aforism_photo"][user_language],
            texts["delete_aforism"][user_language],
            texts["edit_aforism"][user_language],
        ],
        texts["admin_currency"][user_language]: [
            texts["display_current_exchange_rate"][user_language],
            texts["set_new_exchange_rate"][user_language],
        ],
        texts["admin_broadcasts"][user_language]: [
            texts["send_product_broadcast"][user_language],
            texts["send_tag_broadcast"][user_language],
            texts["broadcast_for_all_users"][user_language],
        ],
        texts["admin_applications"][user_language]: [
            texts["view_partner_applications"][user_language],
            texts["support_requests"][user_language],
        ],
        texts["admin_lottery"][user_language]: [
            texts["start_lottery"][user_language],
            texts["end_lottery"][user_language],
            texts["set_lottery_ticket_price"][user_language],
            texts["view_lottery_participants"][user_language],
        ],
        texts["admin_commands"][user_language]: [
            texts['file_command'][user_language],
            texts['new_file_command'][user_language],
        ],
        texts["admin_referral_system"][user_language]: [
            texts["edit_referral_system"][user_language],
            texts["create_referral_system"][user_language],
        ]
    }

    buttons = [[KeyboardButton(text=option)] for option in submenus.get(category, [])]
    buttons.append([KeyboardButton(text=texts["back_to_admin_menu"][user_language])])
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer(f"Выберите действие ({category}):", reply_markup=keyboard)

# Обработчик для кнопки "Назад в админ-меню"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['back_to_admin_menu'].get(lang, '') or '').strip() for lang in texts['back_to_admin_menu']})
async def back_to_admin_menu(message: Message):
    await admin_menu(message)

async def is_admin(user_id: int) -> bool:
    """
    Проверяем, является ли пользователь администратором.
    """
    if user_id == int(ADMIN_ID):  # Главный администратор
        return True

    # Проверка роли в базе данных
    role = await get_user_role(user_id)
    return role == 'admin'


# Команда для добавления партнёра
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_partner_button_admin'].get(lang, '') or '').strip() for lang in texts['add_partner_button_admin']})
async def start_add_partner(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)
    # Проверяем, является ли отправитель администратором
    if not await is_admin(message.from_user.id):
        await message.answer(texts['add_partner_admin_promt'].get(user_language, texts['add_partner_admin_promt']['en']))
        return
    await message.answer(texts['add_partner_send_id'].get(user_language, texts['add_partner_send_id']['en']))
    await state.set_state(AddPartnerState.waiting_for_user_id)


@router.message(AddPartnerState.waiting_for_user_id, F.text.isdigit())
async def process_partner_user_id(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_id = int(message.text)
    user_language = await get_user_language(user_id)
    await state.update_data(user_language=user_language)
    # Устанавливаем роль пользователя как партнёр:
    if user_language == "ru":
        await message.answer(f"Пользователь с user_id {user_id} теперь партнёр!")
    else :
        await message.answer(f"User with user_id {user_id} is now a partner!")
    await state.clear()


@router.message(AddPartnerState.waiting_for_user_id)
async def invalid_partner_user_id(message: Message,state : FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language")  # По умолчанию используем "en"
    if user_language == "ru":
        await message.answer("Пожалуйста, введите корректный user_id (только цифры).")
    else :
        await message.answer("Please enter a valid user_id (numbers only).")


# Команда для добавления администратора
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_admin_button'].get(lang, '') or '').strip() for lang in texts['add_admin_button']})
async def start_add_admin(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)
    # Проверяем, является ли отправитель администратором
    if not await is_admin(message.from_user.id):
        await message.answer(texts['add_partner_admin_promt'].get(user_language, texts['add_partner_admin_promt']['en']))
        return

    await message.answer(texts['add_admin_send_id'].get(user_language, texts['add_admin_send_id']['en']))
    await state.set_state(AddAdminState.waiting_for_user_id)


@router.message(AddAdminState.waiting_for_user_id, F.text.isdigit())
async def process_admin_user_id(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_id = int(message.text)

    # Устанавливаем роль пользователя как администратор
    await set_user_role(user_id, 'admin')
    await message.answer(f"Пользователь с user_id {user_id} теперь администратор!")
    await state.clear()


@router.message(AddAdminState.waiting_for_user_id)
async def invalid_admin_user_id(message: Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    await message.answer("Пожалуйста, введите корректный user_id (только цифры).")

# Обработчик команды "Добавить афоризм"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_aforism'].get(lang, '') or '').strip() for lang in texts['add_aforism']})
async def cmd_add_aphorism(message: types.Message, state: FSMContext):
    user_language = await get_user_language(message.from_user.id)
    await state.update_data(user_language=user_language)
    await message.answer(texts['add_aphorism_promt'].get(user_language, texts['add_aphorism_promt']['en']))
    await state.set_state(AddAphorism.waiting_for_text)

# Принимаем текст афоризма
@router.message(AddAphorism.waiting_for_text)
async def process_aphorism_text(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    await state.update_data(aphorism_text=message.text)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    await state.update_data(user_language=user_language)
    await message.answer(texts['add_aphorism_author'].get(user_language, texts['add_aphorism_author']['en']))
    await state.set_state(AddAphorism.waiting_for_author)

# Принимаем автора афоризма и сохраняем
@router.message(AddAphorism.waiting_for_author)
async def process_aphorism_author(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    data = await state.get_data()
    text = data['aphorism_text']
    author = message.text

    # Сохраняем афоризм в базу данных
    add_aphorism(text, author)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    if user_language == "ru":
        await message.answer("Афоризм был успешно добавлен!")
    else:
        await message.answer("Aphorism was added succesfully!")
    await state.clear()

# Обработчик для команды "Добавить фото афоризма"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_aforism_photo'].get(lang, '') or '').strip() for lang in texts['add_aforism_photo']})
async def cmd_add_image(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    await state.update_data(user_language=user_language)
    await state.set_state(AphorismStates.waiting_for_image)
    await message.answer(texts['aphorism_send_photo'].get(user_language, texts['aphorism_send_photo']['en']))
# Обработчик для сообщений с фото в состоянии waiting_for_image
@router.message(StateFilter(AphorismStates.waiting_for_image), F.content_type == ContentType.PHOTO)
async def process_image_upload(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    file_id = message.photo[-1].file_id  # Получаем file_id изображения
    add_image(file_id)  # Добавляем в базу данных
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    if user_language == "ru":
        await message.answer("Изображение успешно добавлено и будет использоваться с афоризмами!")
        await state.clear()
    else :
        await message.answer("Image successfully added and will be used with aphorisms!")
        await state.clear()
    await state.clear()




# Создаем инлайн-клавиатуру с выбором валюты
def get_currency_keyboard():
    buttons = [
        [InlineKeyboardButton(text="VED", callback_data="update_rate:VED")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Хендлер для запроса выбора валюты
@router.message(lambda message: message.text and message.text.strip() in texts['set_new_exchange_rate'].values())
async def ask_for_currency_selection(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    user_language = await get_user_language(message.from_user.id)  # Определяем язык пользователя
    await state.update_data(user_language=user_language)  # Сохраняем язык в состоянии

    await message.answer(
        texts['aphorism_send_photo'].get(user_language, texts['aphorism_send_photo']['en']),
        reply_markup=get_currency_keyboard()
    )

# Хендлер для обработки нажатий на кнопки
@router.callback_query(F.data.startswith("update_rate:"))
async def handle_currency_selection(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    user_language = state_data.get("user_language", await get_user_language(callback.from_user.id))  # Получаем язык

    currency = callback.data.split(":")[1]  # Получаем выбранную валюту
    await state.update_data(currency=currency)  # Сохраняем валюту в состоянии

    await callback.message.answer(
        f"🛠 Введите новый курс для **{currency}** к USD в формате: `ЧИСЛО`\nПример: `1.15`" if user_language == "ru"
        else f"🛠 Enter new rate for **{currency}** to USD in format: `NUMBER`\n\nExample: `1.15`"
    )

    await state.set_state(RateUpdateState.waiting_for_rate)  # Устанавливаем состояние ожидания ввода курса
    await callback.answer()  # Закрываем уведомление о нажатии кнопки

# Хендлер для ввода нового курса
@router.message(StateFilter(RateUpdateState.waiting_for_rate), F.text)
async def handle_rate_update(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return

    state_data = await state.get_data()
    user_language = state_data.get("user_language", await get_user_language(message.from_user.id))  # Определяем язык
    currency = state_data.get("currency")  # Получаем сохраненную валюту

    try:
        new_rate = float(message.text.strip())  # Конвертируем ввод в число
        update_rate(currency, new_rate)  # Обновляем курс валюты в БД

        await message.answer(
            f"✅ Курс **{currency}** к USD успешно обновлён на **{new_rate}**." if user_language == "ru"
            else f"✅ Rate **{currency}** to USD successfully updated to **{new_rate}**."
        )

    except ValueError:
        await message.answer(
            "❌ Неправильный формат ввода. Введите число.\nПример: `1.15`" if user_language == "ru"
            else "❌ Incorrect input format. Enter a number.\nExample: `1.15`"
        )
    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка при обновлении курса: {e}" if user_language == "ru"
            else f"❌ An error occurred while updating the rate: {e}"
        )
    finally:
        await state.clear()  # Сбрасываем состояние



@router.message(lambda message: message.text and message.text.strip() in {str(texts['display_current_exchange_rate'].get(lang, '') or '').strip() for lang in texts['display_current_exchange_rate']})
async def view_rates(message: Message):
    exchange_rates = await get_exchange_rates()
    btc_usd = exchange_rates.get("BTC/USD", "N/A")
    usdt_usd = exchange_rates.get("USDT/USD", "N/A")
    rub_usd = exchange_rates.get("RUB/USD", "N/A")
    user_language = await get_user_language(message.from_user.id)
    ved_rate = await get_ved_exchange_rate()  # Возвращается строка, преобразуем в float
    ved_rate = float(ved_rate) if ved_rate else 0.0
    ved_rate = round(ved_rate, 2)  # Округляем до 2 знаков после запятой
    # Проверка наличия курсов
    if user_language == "ru":
        response = (
            f"💱 Текущие курсы валют:\n"
            f"1 USDT = {usdt_usd} USD\n"
            f"1 BTC = {btc_usd} USD\n\n"
            f"1 VED = {ved_rate} USD\n"
            f"🔧 Чтобы изменить курс, используйте команду:\n"
            f"Введите: **Установка нового курса валют**\n"
            f"Затем укажите валюту и новый курс."
        )

        await message.answer(response)
    else :
        response = (
            f"💱 Current exchange rates:\n"
            f"{usdt_usd} USD\n"
            f"{btc_usd} USD\n\n"
            f"{rub_usd} USD\n"
            f"{ved_rate} USD\n"
            f"🔧 To change the rate, use the command:\n"
            f"Enter: **Setting a new exchange rate**\n"
            f"Then specify the currency and the new rate."
        )

        await message.answer(response)



@router.message(lambda message: message.text and message.text.strip() in {str(texts['show_pending_products'].get(lang, '') or '').strip() for lang in texts['show_pending_products']})
async def show_pending_products(message: Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    pending_products = get_pending_products()
    user_language = await get_user_language(message.from_user.id)
    if not pending_products:
        if user_language == "ru":
            await message.answer("Нет продуктов, ожидающих подтверждения.")
            return
        else :
            await message.answer("There are no products awaiting confirmation.")
            return

    for product in pending_products:
        # Если это объект sqlite3.Row, приводим его к словарю
        if isinstance(product, sqlite3.Row):
            product = dict(product)
        # Проверяем, что продукт — это словарь и что у него есть ID
        if 'id' not in product:
            continue
        if 'name' not in product or 'description' not in product or 'price' not in product:
            continue
        # Создаем инлайновые кнопки для подтверждения и отклонения
        approve_button = InlineKeyboardButton(text=texts['approve_button'].get(user_language, texts['approve_button']['en']), callback_data=f"approve_{product['id']}")
        reject_button = InlineKeyboardButton(text=texts['reject_button'].get(user_language, texts['reject_button']['en']), callback_data=f"reject_{product['id']}")

        # Создаем клавиатуру для каждого продукта
        inline_buttons = InlineKeyboardMarkup(inline_keyboard=[[approve_button, reject_button]])
        if user_language == "ru":
            # Добавляем информацию о продукте в текст
            product_text = "📝 Продукт, ожидающий подтверждения:\n\n"
            product_text += f"🔹 <b>{product['name']}</b>\n"
            product_text += f"📄 {product['description']}\n"
            product_text += f"💲 Цена: {product['price']}\n"
            product_text += f"💡 Статус: {product['status']}\n"
            product_text += f"📅 Подписка: {'Да' if product['is_subscription'] else 'Нет'}\n"
            if product['is_subscription']:
                product_text += f"🕒 Период подписки: {product.get('subscription_period', 'Не указан')}\n"
            product_text += f"🔑 Уникальный код: {product.get('code', 'Не указан')}\n"
            product_text += f"🖼 Изображение: {product.get('image', 'Нет')}\n"

            # Определяем название категории
            category_text = product.get('category', None)
            if category_text == 'session':
                category_text = 'Онлайн-сессия с терапевтом'
            elif category_text == 'retreat':
                category_text = 'Корпоративный ретрит'
            else:
                category_text = 'Не указана'  # Если категории нет или она не в ожидаемом формате

            product_text += f"📦 Категория: {category_text}\n"
            product_text += f"📍 Партнёр: {product.get('partner_id', 'Не указан')}\n"
            product_text += f"🔒 Скрыт: {'Да' if product['is_hidden'] else 'Нет'}\n"
            product_text += f"🎓 Курс ID: {product.get('course_id', 'Не указан')}\n"
            product_text += f"📅 После покупки: {product.get('after_purchase', 'Не указано')}\n\n"

            # Если есть изображение, отправляем фото
            if product.get("image"):
                await message.answer_photo(
                    photo=product["image"],
                    caption=product_text,
                    reply_markup=inline_buttons,
                    parse_mode="HTML"
                )
            else:
                # Если нет изображения, просто отправляем текст с кнопками
                await message.answer(
                    text=product_text,
                    reply_markup=inline_buttons,
                    parse_mode="HTML"
                )

        else :
            # Add product information to text
            product_text = "📝 Product awaiting confirmation:\n\n"
            product_text += f"🔹 <b>{product['name']}</b>\n"
            product_text += f"📄 {product['description']}\n"
            product_text += f"💲 Price: {product['price']}\n"
            product_text += f"💡 Status: {product['status']}\n"
            product_text += f"📅 Subscription: {'Yes' if product['is_subscription'] else 'No'}\n"
            if product['is_subscription']:
                product_text += f"🕒 Subscription Period: {product.get('subscription_period', 'Not specified')}\n"
            product_text += f"🔑 Unique code: {product.get('code', 'Not specified')}\n"
            product_text += f"🖼 Image: {product.get('image', 'None')}\n"

            # Define the category name
            category_text = product.get('category', None)
            if category_text == 'session':
                category_text = 'Online session with a therapist'
            elif category_text == 'retreat':
                category_text = 'Corporate retreat'
            else:
                category_text = 'Not specified'  # If the category is missing or not in the expected format

                product_text += f"📦 Category: {category_text}\n"
                product_text += f"📍 Partner: {product.get('partner_id', 'Not specified')}\n"
                product_text += f"🔒 Hidden: {'Yes' if product['is_hidden'] else 'No'}\n"
                product_text += f"🎓 Course ID: {product.get('course_id', 'Not specified')}\n"
                product_text += f"📅 After purchase: {product.get('after_purchase', 'Not specified')}\n\n"
            # If there is an image, send a photo
            if product.get("image"):
                await message.answer_photo(
                    photo=product["image"],
                    caption=product_text,
                    reply_markup=inline_buttons,
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    text=product_text,
                    reply_markup=inline_buttons,
                    parse_mode="HTML"
                )


@router.callback_query(lambda c: c.data.startswith('approve_'))
async def approve_product(callback: CallbackQuery):
    product_id = int(callback.data.split('_')[1])  # Извлекаем id продукта
    update_product_status(product_id, 'approved')  # Обновляем статус
    user_language = await get_user_language(callback.from_user.id)
    # Получаем информацию о продукте для уведомления
    product = get_product_by_id(product_id)

    if user_language == "ru":
        await callback.message.answer(f"✅ Продукт '{product['name']}' одобрен и добавлен в каталог.")
    else :
        await callback.message.answer(f"✅ Product '{product['name']}' has been approved and added to the catalog.")


    # Убираем заявку (удаляем сообщение с заявкой)
    try:
        await callback.message.delete()
    except Exception as e:
        if user_language == "ru":
            print(f"Ошибка при удалении сообщения: {e}")
        else :
            print(f"Error deleting message: {e}")

    # Проверяем, содержит ли сообщение текст
    if callback.message.text:
        if user_language == "ru" :
            await callback.message.edit_text("\u2705 Продукт одобрен и добавлен в каталог.")
        else :
            await callback.message.edit_text("\u2705 Product approved and added to catalog.")
    elif callback.message.photo or callback.message.video or callback.message.document:
        if user_language == "ru":
            await callback.answer(
                "Продукт одобрен и добавлен в каталог. (Мультимедийное сообщение не может быть отредактировано.)")
        else :
            await callback.answer(
                "Product approved and added to catalog. (Multimedia message cannot be edited.)")
    else:
        await callback.answer("Не удалось отредактировать сообщение, так как оно не содержит текста.")

    await callback.answer()


@router.callback_query(lambda c: c.data.startswith('reject_'))
async def reject_product(callback: CallbackQuery):
    user_language = await get_user_language(callback.from_user.id)
    product_id = int(callback.data.split('_')[1])  # Извлекаем id продукта
    update_product_status(product_id, 'rejected')  # Обновляем статус

    # Проверка, что сообщение содержит текст
    if callback.message.text:
        if user_language =="ru":
            await callback.message.edit_text("\u274c Продукт отклонён.")
        else :
            await callback.message.edit_text("\u274c Product rejected.")
    else:
        if user_language =="ru":
            await callback.message.answer("\u274c Продукт отклонён.")
        else :
            await callback.message.answer("\u274c Product rejected.")
    await callback.answer()

# Обработчик кнопки "Сделать рассылку"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['send_tag_broadcast'].get(lang, '') or '').strip() for lang in texts['send_tag_broadcast']})
async def admin_send_broadcast(message: types.Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    tags = get_all_tags()
    user_language = await get_user_language(message.from_user.id)
    if not tags:
        if user_language == "ru" :
            await message.answer("Тэги отсутствуют.")
        else :
            await message.answer("No tags.")
        return

    # Клавиатура для выбора тега
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tag, callback_data=f"broadcast_tag:{tag}")]
            for tag in tags
        ]
    )
    if user_language == "ru":
        await message.answer("Выберите тэг для рассылки:", reply_markup=keyboard)
    else :
        await message.answer("Select a tag for the newsletter:", reply_markup=keyboard)


# Обработчик выбора тега для рассылки
@router.callback_query(F.data.startswith("broadcast_tag:"))
async def process_broadcast(callback: CallbackQuery, state: FSMContext):
    tag = callback.data.split(":")[1]
    users = get_users_by_tag(tag)
    user_language = await get_user_language(callback.from_user.id)
    if not users:
        if user_language == "ru":
            await callback.answer("Нет подписчиков на этот тэг.")
        else :
            await callback.answer("No subscribers for this tag.")
        return

    # Сохраняем тэг и список пользователей в состояние
    await state.update_data(tag=tag, users=users)
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
    await state.update_data(user_language=user_language)
    # Устанавливаем состояние ожидания сообщения
    await state.set_state(BroadcastState.waiting_for_message_admin)
    if user_language == "ru":
        await callback.message.answer(
            f"Отправьте сообщение для рассылки по тэгу '{tag}'."
        )
    else :
        await callback.message.answer(
            f"Send a message to the mailing list by tag '{tag}'."
        )


# Обработчик получения сообщения для рассылки
@router.message(BroadcastState.waiting_for_message_admin)
async def broadcast_message(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    try:
        data = await state.get_data()
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
        # Проверяем наличие ключей 'tag' и 'users' в состоянии
        tag = data.get('tag')
        users = data.get('users')

        if not tag or not users:
            if user_language == "ru":
                await message.answer("Ошибка: не удалось получить данные для рассылки.")
            else :
                await message.answer("Error: Failed to get data for mailing.")
            await state.clear()
            return

        sent_count = 0

        for user_id in users:
            try:
                await message.bot.send_message(
                    user_id,
                    f"🔔 Сообщение по тэгу '{tag}':\n{message.text}"
                )
                sent_count += 1
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")

        await message.answer(f"Рассылка завершена. Отправлено сообщений: {sent_count}")

    except Exception as e:
        print(f"Ошибка во время рассылки: {e}")
        await message.answer("Произошла ошибка во время рассылки.")
    finally:
        # Завершаем состояние
        await state.clear()
# Состояния для FSM
class ReferralSystemStateTwo(StatesGroup):
    levels = State()  # Уровни реферальной системы
    rewards = State()  # Награды


# Обработчик кнопки для создания реферальной системы
@router.message(lambda message: message.text and message.text.strip() in {
    str(texts['create_referral_system'].get(lang, '') or '').strip() for lang in texts['create_referral_system']})
async def start_referral_creation(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)
    await state.update_data(user_language=user_language)
    if user_language == "ru":
        await message.answer("Введите количество уровней реферальной системы:")
        await state.set_state(ReferralSystemStateTwo.levels)
    else :
        await message.answer("Enter the number of referral system levels:")
        await state.set_state(ReferralSystemStateTwo.levels)


# Обработчик для ввода количества уровней
@router.message(StateFilter(ReferralSystemStateTwo.levels))
async def set_levels(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    try:
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")  # По умолчанию используем "en"
        await state.update_data(user_language=user_language)
        levels = int(message.text)
        if levels <= 0:
            if user_language == "ru":
                await message.answer("Количество уровней должно быть положительным числом. Попробуйте снова.")
                return
            else :
                await message.answer("Number of levels must be a positive number. Try again.")
                return

        # Сохраняем количество уровней в состоянии
        await state.update_data(levels=levels)

        if user_language == "ru":
            await message.answer(
                f"Теперь введите награды для каждого уровня ({levels} уровней). Например, для первого уровня: 10,5 - где 10 - за покупку, а 5 - за выигрыш в лотереи."
                " Введите награды для каждого уровня в отдельной строке."
                " Вы так же можете ввести награду для одного уровня,одним числом,например : 50 - такая награда будет установлена и за покупку и за выигрыш."
            )
            await state.set_state(ReferralSystemStateTwo.rewards)
        else :
            await message.answer(
                f"Now enter the rewards for each level ({levels} levels). For example, for the first level: 10.5 - where 10 is for a purchase, and 5 is for winning the lottery."
                " Enter the rewards for each level on a separate line."
            )
            await state.set_state(ReferralSystemStateTwo.rewards)

    except ValueError:
        if user_language == "ru":
            await message.answer("Введите корректное число для количества уровней.")
        else :
            await message.answer("Please enter a valid number for the number of levels.")

@router.message(StateFilter(ReferralSystemStateTwo.rewards))
async def set_rewards(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        levels = data.get("levels")
        user_language = data.get("user_language", "en")  # По умолчанию "en"

        # Разделяем введённые данные по строкам (каждая строка - для одного уровня)
        rewards = message.text.strip().split("\n")

        # Проверяем, что количество введённых строк соответствует количеству уровней
        if len(rewards) != levels:
            error_message = (
                f"Вы должны ввести {levels} строк для {levels} уровней. Попробуйте снова."
                if user_language == "ru"
                else f"You must enter {levels} lines for {levels} levels. Try again."
            )
            await message.answer(error_message)
            return

        rewards_list = []
        for reward in rewards:
            # Разделяем строку, но теперь допускаем 1 или 2 значения
            reward_parts = reward.split(",")
            reward_parts = [r.strip() for r in reward_parts if r.strip()]  # Убираем пробелы

            if len(reward_parts) == 1:
                # Если введено одно число, используем его для обеих наград
                try:
                    value = float(reward_parts[0])
                    rewards_list.append([value, value])
                except ValueError:
                    error_message = (
                        "Введите корректное числовое значение. Пример: '50' или '20.5, 50.2'."
                        if user_language == "ru"
                        else "Please enter a valid numeric value. Example: '50' or '20.5, 50.2'."
                    )
                    await message.answer(error_message)
                    return
            elif len(reward_parts) == 2:
                # Если введено два числа, обрабатываем их отдельно
                try:
                    rewards_list.append([float(reward_parts[0]), float(reward_parts[1])])
                except ValueError:
                    error_message = (
                        "Введите корректные числовые значения. Пример: '50' или '20.5, 50.2'."
                        if user_language == "ru"
                        else "Please enter valid numeric values. Example: '50' or '20.5, 50.2'."
                    )
                    await message.answer(error_message)
                    return
            else:
                error_message = (
                    "Формат неверен. Введите одно число (для обоих значений) или два числа через запятую."
                    if user_language == "ru"
                    else "Invalid format. Enter a single number (for both values) or two numbers separated by a comma."
                )
                await message.answer(error_message)
                return

        # Сохраняем награды в состоянии
        await state.update_data(rewards=rewards_list)

        # Вызываем создание реферальной системы
        create_referral_system(levels, rewards_list)

        success_message = (
            f"Реферальная система создана:\nУровни: {levels}\nНаграды: {rewards_list}"
            if user_language == "ru"
            else f"Referral system created:\nLevels: {levels}\nRewards: {rewards_list}"
        )
        await message.answer(success_message)
        await state.clear()

    except Exception as e:
        # Обработка других ошибок
        error_message = (
            "Произошла ошибка. Попробуйте снова."
            if user_language == "ru"
            else "An error occurred. Please try again."
        )
        await message.answer(error_message)
        print(f"Error in set_rewards: {e}")

class ReferralSystemState(StatesGroup):
    levels = State()  # Уровни реферальной системы
    rewards = State()  # Награды
    edit_level = State()  # Редактирование уровня
    edit_purchase = State()  # Редактирование награды за покупку
    edit_lottery = State()  # Редактирование награды за лотерею

# Обработчик кнопки для редактирования реферальной системы
@router.message(lambda message: message.text and any(
    message.text.strip() == str(texts['edit_referral_system'].get(lang, '')).strip() for lang in texts['edit_referral_system']
))
async def start_referral_editing(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_id = message.from_user.id
    user_language = await get_user_language(message.from_user.id)  # Получаем язык пользователя
    current_system = get_current_referral_system()
    current_levels = current_system['levels']
    current_rewards = current_system['rewards']

    rewards_text = "\n".join(
        f"Уровень {level}: Покупка {rewards[0]}, Лотерея {rewards[1]}" if user_language == "ru"
        else f"Level {level}: Purchase {rewards[0]}, Lottery {rewards[1]}"
        for level, rewards in current_rewards.items()
    )

    inline_keyboard = [
        [InlineKeyboardButton(
            text=f"Уровень {level}" if user_language == "ru" else f"Level {level}",
            callback_data=f"edit_reward_{level}"
        )]
        for level in current_rewards.keys()
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    await message.answer(
        f"Текущие настройки:\nУровни: {current_levels}\nНаграды:\n{rewards_text}\n\nВыберите уровень для изменения награды:"
        if user_language == "ru" else
        f"Current settings:\nLevels: {current_levels}\nRewards:\n{rewards_text}\n\nSelect a level to edit the reward:",
        reply_markup=keyboard
    )

    await state.set_state(ReferralSystemState.edit_level)
    await state.update_data(current_system=current_system)

# Обработчик для выбора уровня
@router.callback_query(lambda callback: callback.data.startswith("edit_reward_"))
async def edit_reward_callback(query: types.CallbackQuery, state: FSMContext):
    user_language = await get_user_language(query.from_user.id)
    level = int(query.data.split("_")[-1])

    inline_keyboard = [
        [
            InlineKeyboardButton(
                text="Покупка Бонус" if user_language == "ru" else "Purchase Bonus",
                callback_data=f"edit_purchase_{level}"
            ),
            InlineKeyboardButton(
                text="Лотерея" if user_language == "ru" else "Lottery",
                callback_data=f"edit_lottery_{level}"
            )
        ],
        [InlineKeyboardButton(
            text="Отмена" if user_language == "ru" else "Cancel",
            callback_data="cancel"
        )]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard, row_width=2)

    await query.message.edit_text(
        f"Вы выбрали уровень {level}. Выберите награду для изменения:" if user_language == "ru"
        else f"You have selected level {level}. Choose the reward to edit:",
        reply_markup=keyboard
    )
    await state.update_data(edit_level=level)
    await query.answer()

# Обработчик для изменения награды за покупку
@router.callback_query(lambda callback: callback.data.startswith("edit_purchase_"))
async def edit_purchase_callback(query: types.CallbackQuery, state: FSMContext):
    user_language = await get_user_language(query.from_user.id)
    level = int(query.data.split("_")[-1])
    await query.message.edit_text(
        f"Введите новую награду за покупку для уровня {level}:" if user_language == "ru"
        else f"Enter the new purchase reward for level {level}:"
    )
    await state.set_state(ReferralSystemState.edit_purchase)

# Обработчик для изменения награды за лотерею
@router.callback_query(lambda callback: callback.data.startswith("edit_lottery_"))
async def edit_lottery_callback(query: types.CallbackQuery, state: FSMContext):
    user_language = await get_user_language(query.from_user.id)
    level = int(query.data.split("_")[-1])
    await query.message.edit_text(
        f"Введите новую награду за лотерею для уровня {level}:" if user_language == "ru"
        else f"Enter the new lottery reward for level {level}:"
    )
    await state.set_state(ReferralSystemState.edit_lottery)

# Обработчик ввода новой награды за покупку
@router.message(StateFilter(ReferralSystemState.edit_purchase))
async def set_new_purchase_reward(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)
    try:
        new_reward = int(message.text.strip())
        data = await state.get_data()
        level = data['edit_level']
        current_system = data['current_system']
        current_system['rewards'][level][0] = new_reward
        await state.update_data(current_system=current_system)
        update_referral_rewards(level, current_system['rewards'][level])  # Обновляем в БД

        await message.answer(
            f"Новая награда за покупку для уровня {level} установлена: {new_reward}." if user_language == "ru"
            else f"New purchase reward for level {level} set to: {new_reward}."
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректное число для награды." if user_language == "ru"
            else "Please enter a valid number for the reward."
        )

# Обработчик ввода новой награды за лотерею
@router.message(StateFilter(ReferralSystemState.edit_lottery))
async def set_new_lottery_reward(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)
    try:
        new_reward = int(message.text.strip())
        data = await state.get_data()
        level = data['edit_level']
        current_system = data['current_system']
        current_system['rewards'][level][1] = new_reward
        await state.update_data(current_system=current_system)
        update_referral_rewards(level, current_system['rewards'][level])  # Обновляем в БД

        await message.answer(
            f"Новая награда за лотерею для уровня {level} установлена: {new_reward}." if user_language == "ru"
            else f"New lottery reward for level {level} set to: {new_reward}."
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректное число для награды." if user_language == "ru"
            else "Please enter a valid number for the reward."
        )

# Обработчик кнопки "Отмена"
@router.callback_query(lambda callback: callback.data.startswith("cancel"))
async def cancel_editing(query: types.CallbackQuery, state: FSMContext):
    user_language = await get_user_language(query.from_user.id)
    await query.message.edit_text(
        "Редактирование отменено." if user_language == "ru"
        else "Editing cancelled."
    )
    await state.clear()

# Обработка нажатия на кнопку "Сделать рассылку по продукту"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['send_product_broadcast'].get(lang, '') or '').strip() for lang in texts['send_product_broadcast']})
async def send_product_message(msg: types.Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id) # Предположим, что язык пользователя уже определен

    # Получаем все продукты из базы данных
    products = get_all_products_two()

    # Создаем инлайн-кнопки для каждого продукта
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=[])
    for product in products:
        button = InlineKeyboardButton(
            text=f"ID:{product['id']} - {product['name']}",
            callback_data=f"send_product_{product['id']}"
        )
        keyboard.inline_keyboard.append([button])

    # Отправляем сообщение с кнопками
    if user_language == "ru":
        await msg.answer("Выберите продукт для рассылки:", reply_markup=keyboard)
    else:
        await msg.answer("Select a product for the broadcast:", reply_markup=keyboard)

# Обработка выбора продукта
@router.callback_query(lambda c: c.data.startswith('send_product_'))
async def handle_product_selection(callback_query: types.CallbackQuery, state: FSMContext):
    user_language = "ru"  # Предположим, что язык пользователя уже определен
    product_id = int(callback_query.data.split('_')[2])

    # Сохраняем ID выбранного продукта в состоянии
    await state.update_data(product_id=product_id)

    # Запрашиваем сообщение для рассылки
    if user_language == "ru":
        await callback_query.answer("Введите сообщение для рассылки по продукту.")
        await callback_query.bot.send_message(
            callback_query.from_user.id,
            "Введите текст сообщения, которое вы хотите отправить всем пользователям, купившим этот продукт."
        )
    else:
        await callback_query.answer("Enter the message for the product broadcast.")
        await callback_query.bot.send_message(
            callback_query.from_user.id,
            "Enter the text of the message you want to send to all users who purchased this product."
        )

    # Переходим в состояние ожидания ввода сообщения
    await state.set_state(ProductMessageState.waiting_for_message)

# Обработка ввода сообщения
@router.message(ProductMessageState.waiting_for_message)
async def process_message_for_product(msg: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = "ru"  # Предположим, что язык пользователя уже определен
    user_data = await state.get_data()
    product_id = user_data.get('product_id')
    message_text = msg.text

    # Логика для рассылки по продукту
    users = get_users_by_product(product_id)

    # Рассылка сообщения пользователям
    for user in users:
        try:
            await msg.bot.send_message(user['user_id'], message_text)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user['user_id']}: {e}")

    # Информируем администратора, что рассылка завершена
    if user_language == "ru":
        await msg.answer("Рассылка по продукту завершена.")
    else:
        await msg.answer("Product broadcast completed.")

    # Завершаем состояние
    await state.clear()


@router.message(lambda message: message.text and message.text.strip() in {str(texts['view_all_products'].get(lang, '') or '').strip() for lang in texts['view_all_products']})
async def send_product_page(message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    chat_id = message.chat.id  # Извлекаем chat_id из объекта message
    page = 1  # Страница по умолчанию

    products = get_all_products()  # Получаем список продуктов
    # Фильтруем только те продукты, которые не скрыты и имеют статус approved
    visible_products = [
        p for p in products
        if p.get("status") == "approved"  # Правильная фильтрация
    ]

    total_pages = ceil(len(visible_products) / ITEMS_PER_PAGE)  # Количество страниц
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    products_to_show = visible_products[start_index:end_index]

    text = "📋 Список продуктов:\n\n"
    for product in products_to_show:
        name = product["name"] if not product.get("is_personal") else "Продукт доступен по коду"
        text += f"🔹 {name} — {product['price']} VED\n"

    keyboard_buttons = []

    for product in products_to_show:
        button_text = f"ℹ {product['name']} - {product['price']} VED"
        callback_data = f"info_admin_{product['id']}"  # Используем ID продукта
        keyboard_buttons.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page-1}"))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"page_{page+1}"))

    keyboard_buttons.extend(navigation_buttons)
    keyboard_buttons.append(InlineKeyboardButton(text="🔍 Поиск по коду", callback_data="search_product_by_code_admin"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[keyboard_buttons])

    await message.bot.send_message(chat_id, text, reply_markup=keyboard)

# Пагинация продуктов
@router.message(lambda message: message.text == "⬅️ Previous" or message.text == "➡️ Next")
async def paginate_products(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    # Получаем текущую страницу и обрабатываем переход
    user_data = await state.get_data()
    current_page = user_data.get("current_page", 1)

    if message.text == "⬅️ Previous":
        current_page -= 1
    elif message.text == "➡️ Next":
        current_page += 1

    await state.update_data(current_page=current_page)

    # Отправляем новую страницу продуктов
    await send_product_page(message.chat.id, current_page)


@router.callback_query(lambda callback: callback.data == "search_product_by_code_admin")
async def search_product_by_code_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите код продукта для поиска.")  # Запрашиваем код продукта
    await state.set_state("search_product_by_code")  # Устанавливаем состояние, чтобы ожидать код
    await callback.answer()  # Ответ на инлайн кнопку


@router.callback_query(lambda callback: callback.data.startswith("info_admin_"))
async def product_info_handler(callback: CallbackQuery):
    try:
        callback_data_parts = callback.data.split("_")
        if len(callback_data_parts) < 3:
            raise ValueError("Некорректные данные callback.")
        product_id = int(callback_data_parts[2])  # Извлекаем ID продукта
    except (IndexError, ValueError) as e:
        await callback.message.answer("❌ Ошибка в данных продукта.")
        print(f"Ошибка при извлечении ID продукта: {e}")
        return

    # Получаем продукт и информацию о пользователе
    product = get_product_by_id(product_id)
    if not product:
        await callback.message.answer("❌ Продукт не найден.")
        print(f"Продукт с ID {product_id} не найден.")
        return
    user_id = callback.from_user.id
    user_balance = await get_user_balance(user_id)  # Обновлено: функция асинхронная

    if not product:
        await callback.message.answer("❌ Продукт не найден.")
        return

    # Сопоставление категорий
    category_mapping = {
        "session": "Онлайн-Сессия с терапевтом",
        "retreat": "Корпоративный ретрит"
    }
    category_text = category_mapping.get(product["category"], product["category"])

    # Проверка подписки
    if product["is_subscription"]:
        subscription_text = f"Подписка на {product['subscription_period']} дней"
    else:
        subscription_text = "Не подписка"

    # Формируем сообщение о продукте
    product_text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"💰 Цена: {product['price']} VED\n"
        f"📋 Категория: {category_text}\n"
        f"🔖 Статус: {subscription_text}\n"
        f"💳 Ваш баланс: {user_balance} VED"
    )

    # Создаем клавиатуру с кнопкой "Купить", если у пользователя хватает средств
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if user_balance >= product["price"]:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="🛒 Купить",
                callback_data=f"buy_product_{product_id}"
            )
        ])

    # Отправляем информацию о продукте
    try:
        if product.get("image"):
            await callback.message.answer_photo(
                photo=product["image"],
                caption=product_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                text=product_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        await callback.message.answer("❌ Не удалось отправить информацию о продукте.")
        print(f"Ошибка отправки сообщения: {e}")

# Получаем заявки на партнёрство
@router.message(lambda message: message.text and message.text.strip() in {str(texts['view_partner_applications'].get(lang, '') or '').strip() for lang in texts['view_partner_applications']})
async def show_partnership_requests(message: types.Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)  # Предположим, что язык пользователя уже определен

    # Получаем все заявки на партнёрство со статусом 'pending'
    partners = get_partners_with_status('pending')
    if not partners:
        if user_language == "ru":
            await message.answer("Нет заявок на партнёрство.", reply_markup=admin_menu())
        else:
            await message.answer("No partnership applications.", reply_markup=admin_menu())
        return

    # Формируем сообщение с заявками
    for partner in partners:
        partner_id = partner[0]
        partner_name = partner[1]
        partner_credo = partner[2]
        partner_logo_url = partner[3]
        partner_show_in_list = partner[4]
        partner_status = partner[5]
        partner_real_id = partner[6]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=f"Принять {partner_name}" if user_language == "ru" else f"Accept {partner_name}",
                callback_data=f"accept_{partner_real_id}"
            ),
            InlineKeyboardButton(
                text=f"Отклонить {partner_name}" if user_language == "ru" else f"Reject {partner_name}",
                callback_data=f"mem_{partner_real_id}"
            )
        ]])

        caption = (
            f"Заявка от {partner_name}.\nКредо: {partner_credo}\n"
            f"Показать в списке: {'Да' if partner_show_in_list else 'Нет'}\n"
            f"Статус: {partner_status}"
            if user_language == "ru"
            else
            f"Application from {partner_name}.\nCredo: {partner_credo}\n"
            f"Show in list: {'Yes' if partner_show_in_list else 'No'}\n"
            f"Status: {partner_status}"
        )

        if partner_logo_url:
            await message.answer_photo(photo=partner_logo_url, caption=caption, reply_markup=keyboard)
        else:
            await message.answer(caption, reply_markup=keyboard)

# Обработка принятия или отклонения заявки
@router.callback_query(lambda c: c.data.startswith("accept_") or c.data.startswith("mem_"))
async def handle_partnership_action(callback_query: types.CallbackQuery):
    user_language = await get_user_language(callback_query.from_user.id)  # Предположим, что язык пользователя уже определен
    action = callback_query.data.split('_')[0]
    user_id = int(callback_query.data.split('_')[1])

    logging.debug(f"Действие: {action}, user_id: {user_id}")

    user = get_user_by_id_admin(user_id)
    if not user:
        logging.error(f"Не удалось найти пользователя с user_id {user_id}.")
        await callback_query.answer(
            "Не удалось найти пользователя." if user_language == "ru" else "Could not find the user."
        )
        return

    logging.debug(f"Пользователь найден: ID={user['user_id']}, Role={user['role']}")

    if action == "accept":
        partner_id = user_id
        update_partner_status(partner_id, 'approved')
        if user['role'] != 'admin':
            update_user_role_for_partner(user_id, 'partner')
            logging.info(f"Роль пользователя с ID {user_id} изменена на 'partner'.")

        await callback_query.answer(
            "Заявка принята и роль обновлена." if user_language == "ru" else "Application accepted and role updated."
        )
        logging.info(f"Заявка от пользователя с ID {user_id} принята.")
    elif action == "mem":
        partner_id = user_id
        update_partner_status(partner_id, 'rejected')
        await callback_query.answer(
            f"Заявка от {partner_id} отклонена." if user_language == "ru" else f"Application from {partner_id} rejected."
        )

    await show_partnership_requests(callback_query.message)
    logging.debug("Отправлен обновлённый список заявок.")


@router.message(lambda message: message.text and message.text.strip() in {str(texts['support_requests'].get(lang, '') or '').strip() for lang in texts['support_requests']})
async def view_feedbacks(message: types.Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)
    feedbacks = get_feedbacks()

    if user_language == "ru":
        response_text = "Обращения в поддержку:\n\n"
    else :
        response_text = "Support requests:\n\n"
    for feedback in feedbacks:
        user_id, feedback_text, created_at = feedback
        if user_language == "ru":
            response_text += f"USER_ID: {user_id}\nОбращение:{feedback_text}\n{created_at}\n\n"
        else :
            response_text += f"USER_ID: {user_id}\nRequest:{feedback_text}\n{created_at}\n\n"

    # Отправляем текст админу
    await message.answer(response_text)



@router.message(lambda message: message.text and message.text.strip() in {str(texts['delete_aforism'].get(lang, '') or '').strip() for lang in texts['delete_aforism']})
async def cmd_delete_aphorism(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    # Получаем список всех афоризмов из базы данных
    aphorisms = get_all_aphorisms()
    user_language = await get_user_language(message.from_user.id)
    if not aphorisms:
        if user_language == "ru":
            await message.answer("В базе данных нет афоризмов для удаления.")
            return
        else :
            await message.answer("There are no aphorisms in the database to delete.")
            return

    await state.update_data(user_language=user_language)
    if user_language == 'ru':
        aphorisms_text = "Список афоризмов:\n\n" + "\n".join(
            [f"{aphorism['id']}: {aphorism['text']} (Автор: {aphorism['author']})" for aphorism in aphorisms]
        )
        await message.answer(aphorisms_text)
    else :
        aphorisms_text = "List of aphorisms:\n\n" + "\n".join(
            [f"{aphorism['id']}: {aphorism['text']} (Author: {aphorism['author']})" for aphorism in aphorisms]
        )
        await message.answer(aphorisms_text)


    if user_language == "ru":
        await message.answer("Пожалуйста, введите ID афоризма, который вы хотите удалить:")
        await state.set_state(DeleteAphorism.waiting_for_id)
    else :
        await message.answer("Please enter the ID of the aphorism you want to delete:")


# Принимаем ID афоризма и удаляем его
@router.message(DeleteAphorism.waiting_for_id)
async def process_aphorism_id(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    try:
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")
        aphorism_id = int(message.text)
        # Проверяем, существует ли афоризм с указанным ID
        if not aphorism_exists(aphorism_id):
            if user_language == 'ru':
                await message.answer("Афоризм с таким ID не найден. Убедитесь, что вы ввели правильный ID.")
            else :
                await message.answer("Aphorism with such ID was not found. Make sure you entered the correct ID.")
        else:
            # Удаляем афоризм из базы данных
            delete_aphorism(aphorism_id)
            if user_language == "ru":
                await message.answer("Афоризм был успешно удалён!")
            else :
                await message.answer("The aphorism was successfully deleted!")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный числовой ID.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при удалении афоризма: {e}")
    finally:
        await state.clear()


@router.message(lambda message: message.text and message.text.strip() in {str(texts['edit_aforism'].get(lang, '') or '').strip() for lang in texts['edit_aforism']})
async def cmd_edit_aphorism(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    # Получаем список всех афоризмов
    aphorisms = get_all_aphorisms()
    user_language = await get_user_language(message.from_user.id)
    await state.update_data(user_language=user_language)
    if not aphorisms:
        if user_language == "ru":
            await message.answer("В базе данных нет афоризмов для изменения.")
            return
        else :
            await message.answer("There are no aphorisms in the database to change.")
            return

    # Формируем список афоризмов для выбора
    if user_language == "ru":
        aphorisms_text = "Список афоризмов:\n\n" + "\n".join(
            [f"{aphorism['id']}: {aphorism['text']} (Автор: {aphorism['author']})" for aphorism in aphorisms]
        )
        await message.answer(aphorisms_text)
    else :
        aphorisms_text = "List of aphorisms:\n\n" + "\n".join(
            [f"{aphorism['id']}: {aphorism['text']} (Author: {aphorism['author']})" for aphorism in aphorisms]
        )
        await message.answer(aphorisms_text)


    # Просим ввести ID афоризма для изменения
    if user_language == "ru":
        await message.answer("Пожалуйста, введите ID афоризма, который вы хотите изменить:")
        await state.set_state(EditAphorism.waiting_for_id)
    else :
        await message.answer("Please enter the ID of the aphorism you want to edit:")
        await state.set_state(EditAphorism.waiting_for_id)

# Получаем ID афоризма
@router.message(EditAphorism.waiting_for_id)
async def process_edit_aphorism_id(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    try:
        state_data = await state.get_data()
        user_language = state_data.get("user_language", "en")
        await state.update_data(user_language=user_language)
        aphorism_id = int(message.text)

        if not aphorism_exists(aphorism_id):
            if user_language == "ru":
                await message.answer("Афоризм с таким ID не найден. Убедитесь, что вы ввели правильный ID.")
                return
            else:
                await message.answer("Aphorism with such ID was not found. Make sure you entered the correct ID.")
                return

        # Сохраняем ID афоризма в состоянии
        await state.update_data(aphorism_id=aphorism_id)

        if user_language == "ru":
            await message.answer("Что вы хотите изменить?\n\n1. Текст\n2. Автора\n\nВведите 1 или 2:")
            await state.set_state(EditAphorism.waiting_for_choice)
        else :
            await message.answer("What do you want to change?\n\n1. Text\n2. Author\n\nEnter 1 or 2:")
            await state.set_state(EditAphorism.waiting_for_choice)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный числовой ID.")

# Получаем выбор: текст или автор
@router.message(EditAphorism.waiting_for_choice)
async def process_edit_choice(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    choice = message.text.strip()

    if choice == "1":
        if user_language == "ru":
            await message.answer("Введите новый текст афоризма:")
            await state.set_state(EditAphorism.waiting_for_new_text)
        else :
            await message.answer("Enter new aphorism text:")
            await state.set_state(EditAphorism.waiting_for_new_text)
    elif choice == "2":
        if user_language == "ru":
            await message.answer("Введите нового автора афоризма:")
            await state.set_state(EditAphorism.waiting_for_new_author)
        else :
            await message.answer("Enter a new aphorism author:")
            await state.set_state(EditAphorism.waiting_for_new_author)
    else:
        if user_language == "ru" :
            await message.answer("Пожалуйста, введите 1 или 2 для выбора.")
        else :
            await message.answer("Please enter 1 or 2 to choose.")

# Обновляем текст афоризма
@router.message(EditAphorism.waiting_for_new_text)
async def process_new_text(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    new_text = message.text
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    data = await state.get_data()
    aphorism_id = data['aphorism_id']

    update_aphorism_text(aphorism_id, new_text)
    if user_language == "ru":
        await message.answer("Текст афоризма был успешно обновлён!")
        await state.clear()
    else :
        await message.answer("The aphorism text was successfully updated!")
        await state.clear()


# Обновляем автора афоризма
@router.message(EditAphorism.waiting_for_new_author)
async def process_new_author(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    new_author = message.text
    data = await state.get_data()
    aphorism_id = data['aphorism_id']
    state_data = await state.get_data()
    user_language = state_data.get("user_language", "en")
    update_aphorism_author(aphorism_id, new_author)
    if user_language == 'ru':
        await message.answer("Автор афоризма был успешно обновлён!")
        await state.clear()
    else :
        await message.answer("The author of the aphorism was successfully updated!")
        await state.clear()


@router.message(lambda message: message.text and message.text.strip() in {str(texts['view_all_users'].get(lang, '') or '').strip() for lang in texts['view_all_users']})
async def show_all_users(message: types.Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    # Получаем список пользователей из базы данных
    users = get_all_users()
    user_language = await get_user_language(message.from_user.id)
    if not users:
        if user_language == "ru":
            await message.answer("Пользователей пока нет.")
        else :
            await message.answer("No users yet")
    else:
        if user_language == "ru":
            user_list = "\n".join([f"ID: {user['user_id']}, Имя: {user['username']}" for user in users])
            await message.answer(f"Список пользователей:\n{user_list}")
        else :
            user_list = "\n".join([f"ID: {user['user_id']}, Name: {user['username']}" for user in users])
            await message.answer(f"User list:\n{user_list}")

@router.message(lambda message: message.text and message.text.strip() in {str(texts['view_users_with_balance'].get(lang, '') or '').strip() for lang in texts['view_users_with_balance']})
async def show_users_with_balance(message: types.Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    # Получаем список пользователей с балансом больше 0
    users = get_users_with_balance()
    user_language = await get_user_language(message.from_user.id)

    if not users:
        if user_language == "ru":
            await message.answer("Нет пользователей с балансом больше 0.")
        else:
            await message.answer("No users with a balance greater than 0.")
    else:
        if user_language == "ru":
            user_list = "\n".join([f"ID: {user['user_id']}, Имя: {user['username']}, Баланс: {user['balance']}" for user in users])
            await message.answer(f"Список пользователей с балансом:\n{user_list}")
        else:
            user_list = "\n".join([f"ID: {user['user_id']}, Name: {user['username']}, Balance: {user['balance']}" for user in users])
            await message.answer(f"Users with balance:\n{user_list}")



# Хендлер нажатия на кнопку "Добавить пользователю баланс"
@router.message(lambda message: message.text and message.text.strip() in {str(texts['add_balance_to_user'].get(lang, '') or '').strip() for lang in texts['add_balance_to_user']})
async def start_add_balance(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)
    if user_language == "ru":
        await message.answer("Введите ID пользователя, которому нужно добавить баланс:")
        await state.set_state(AddBalanceStates.waiting_for_user_id)
    else :
        await message.answer("Enter the ID of the user you want to add balance to:")
        await state.set_state(AddBalanceStates.waiting_for_user_id)



# Хендлер ввода ID пользователя
@router.message(AddBalanceStates.waiting_for_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    if not message.text.isdigit():
        await message.answer("ID пользователя должно быть числом. Попробуйте ещё раз:")
        return

    await state.update_data(user_id=int(message.text))
    await message.answer("Введите сумму, на которую нужно увеличить баланс:")
    await state.set_state(AddBalanceStates.waiting_for_amount)


# Хендлер ввода суммы
@router.message(AddBalanceStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    if not message.text.isdigit():
        await message.answer("Сумма должна быть числом. Попробуйте ещё раз:")
        return

    data = await state.get_data()
    user_id = data["user_id"]
    amount = int(message.text)

    # Добавляем баланс пользователю
    if add_balance_to_user(user_id, amount):
        await message.answer(f"Баланс пользователя с ID {user_id} успешно увеличен на {amount}.")
    else:
        await message.answer(f"Ошибка: Пользователь с ID {user_id} не найден.")

    await state.clear()

@router.message(
    lambda message: message.text and message.text.strip() in {str(texts['start_lottery'].get(lang, '') or '').strip()
                                                              for lang in texts['start_lottery']})
async def start_lottery(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    await message.reply("Какая награда будет для утешительных билетов?")
    await state.set_state("waiting_for_consolation_prize")


@router.message(StateFilter("waiting_for_consolation_prize"))
async def receive_consolation_prize(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    consolation_prize = message.text.strip()
    await state.update_data(consolation_prize=consolation_prize)

    await message.reply("Введите размер призового фонда:")
    await state.set_state("waiting_for_fund")


@router.message(StateFilter("waiting_for_fund"))
async def receive_fund(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    try:
        fund = int(message.text.strip())
        if fund < 0:
            raise ValueError
    except ValueError:
        await message.reply("Ошибка! Введите корректное положительное число для фонда:")
        return

    await state.update_data(fund=fund)

    await message.reply("Введите цену за один билет:")
    await state.set_state("waiting_for_ticket_price")


@router.message(StateFilter("waiting_for_ticket_price"))
async def receive_ticket_price(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    try:
        ticket_price = float(message.text.strip())
        if ticket_price < 0:
            raise ValueError
    except ValueError:
        await message.reply("Ошибка! Введите корректную цену за билет (положительное число):")
        return

    await state.update_data(ticket_price=ticket_price)

    # Запрос на выбор локации для лотереи (ТГ-канал или бот)
    await message.reply("Где будет проводиться лотерея? Введите 'Канал' или 'Бот':")
    await state.set_state("waiting_for_location")


@router.message(StateFilter("waiting_for_location"))
async def receive_location(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    location = message.text.strip().lower()
    if location not in ['канал', 'бот']:
        await message.reply("Ошибка! Пожалуйста, введите 'Канал' или 'Бот'.")
        return

    await state.update_data(location=location)

    data = await state.get_data()
    fund = data.get("fund")
    ticket_price = data.get("ticket_price")
    location = data.get("location")

    with connect_db() as conn:
        cursor = conn.cursor()

        # Завершаем предыдущую лотерею
        cursor.execute("UPDATE lottery SET active = 0 WHERE active = 1")

        # Создаем новую лотерею с указанной локацией
        cursor.execute(
            "INSERT INTO lottery (name, ticket_price, fund, location, active) VALUES (?, ?, ?, ?, ?)",
            ("Месячная лотерея", ticket_price, fund, location, 1)
        )

        conn.commit()

    users = get_all_users()
    if not users:
        await message.answer("Пользователей пока нет.")
    else:
        for user in users:
            user_id = user["user_id"]
            user_language = await get_user_language(user_id)
            lottery_start_message = texts['lottery_start'].get(user_language, texts['lottery_start']['en'])
            try:
                await message.bot.send_message(user_id, lottery_start_message)
            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

    await state.clear()
    await message.reply(f"Лотерея началась! Призовой фонд: {fund}, цена билета: {ticket_price}, место проведения: {location.capitalize()}!")



@router.message(
    lambda message: message.text and message.text.strip() in {str(texts['end_lottery'].get(lang, '') or '').strip()
                                                              for lang in texts['end_lottery']}
)
async def end_lottery(message: types.Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    user_language = await get_user_language(message.from_user.id)

    # Получаем информацию о текущей активной лотерее
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, fund FROM lottery WHERE active = 1 ORDER BY id DESC LIMIT 1")
        active_lottery = cursor.fetchone()

    if not active_lottery:
        await message.reply("Ошибка! Активная лотерея не найдена.")
        return

    lottery_id, total_fund = active_lottery  # Общий фонд лотереи
    logging.info(f"Общий фонд лотереи: {total_fund} VED")

    # Получаем общее количество билетов
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM lottery_tickets WHERE lottery_id = ?", (lottery_id,))
        total_tickets_count = cursor.fetchone()[0]

    # Призовые билеты должны быть назначены после покупки
    await assign_prizes_to_tickets(lottery_id, total_tickets_count)

    # Получаем все билеты
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, ticket_number FROM lottery_tickets WHERE lottery_id = ? AND prize != 'Пустой'", (lottery_id,))
        tickets = cursor.fetchall()

    if not tickets:
        await message.reply("Лотерея завершена, но выигрышных билетов нет.")
        return

    # Логируем информацию о билетах
    for ticket in tickets:
        id, user_id, ticket_number = ticket
        logging.info(f"Билет {id} | Пользователь ID: {user_id} | Номер билета: {ticket_number}")

    # Получаем проценты на реферальные выплаты
    referral_system_id = get_referral_system_id()
    if not referral_system_id:
        await message.reply("Ошибка! Активная реферальная система не найдена.")
        return

    # Получаем проценты на реферальные выплаты
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(""" 
            SELECT level, amount FROM referral_rewards
            WHERE referral_system_id = ? AND reward_type = 'lottery'
        """, (referral_system_id,))
        reward_percentages = {row[0]: row[1] for row in cursor.fetchall()}  # {1: 50, 2: 30, 3: 20}

        referral_percentage = sum(reward_percentages.values())
        referral_fund = (total_fund * referral_percentage) / 100  # Фонд для реферальных
        logging.info(f"Реферальный фонд: {referral_fund} VED")

        # Призовой фонд после вычета реферальных выплат
        prize_fund = total_fund - referral_fund
        logging.info(f"Призовой фонд: {prize_fund} VED")

    # Категории призов
    winning_categories = ['10%'] * 9 + ['1%'] * 9 + ['0.1%'] * 9 + ['0.01%'] * 9 + ['0.001%'] * 9 + ['0.0001%'] * 9
    random.shuffle(winning_categories)

    # Распределяем призы
    prize_map = {ticket: winning_categories[i] if i < len(winning_categories) else 'Утешительный приз'
                 for i, ticket in enumerate(tickets)}

    # Обрабатываем победителей и начисляем бонусы рефералам
    for ticket in tickets:
        id, user_id, ticket_number = ticket

        if user_id is None:
            logging.error(f"Ошибка: билет {id} имеет user_id=None")
            continue

        prize_category = prize_map.get(ticket, 'Утешительный приз')

        if prize_category in winning_categories:
            prize_amount = calculate_prize(prize_fund, prize_category)  # Расчёт выигрыша
            logging.info(f"Билет {id}: {prize_category}, выигрыш = {prize_amount} VED")

            if prize_amount == 0.0:
                logging.warning(f"ВНИМАНИЕ: Билет {id} получил {prize_amount} VED!")

            # Обновляем баланс пользователя
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute(""" 
                    UPDATE users
                    SET balance = balance + ?
                    WHERE user_id = ?
                """, (prize_amount, user_id))  # Добавляем выигранную сумму на баланс
                conn.commit()

            prize_message = texts['prize_message'].get(user_language, texts['prize_message']['en']).format(
                ticket_number=ticket_number, prize_amount=prize_amount, prize_category=prize_category
            )
        else:
            prize_message = texts['prize_message_utesh'].get(user_language, texts['prize_message_utesh']['en']).format(
                ticket_number=ticket_number
            )

        try:
            await message.bot.send_message(int(user_id), prize_message)
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

        # Начисление реферальных бонусов
        current_user_id = user_id

        # Получаем уровень пользователя, который выиграл
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT level FROM referrals WHERE referred_id = ?", (current_user_id,))
            current_user_level = cursor.fetchone()

        if not current_user_level:
            logging.error(f"Ошибка: У пользователя {current_user_id} нет уровня в системе.")
            continue

        current_user_level = current_user_level[0]

        # Получаем проценты на реферальные выплаты
        referral_system_id = get_referral_system_id()
        if not referral_system_id:
            await message.reply("Ошибка! Активная реферальная система не найдена.")
            return

        # Получаем проценты на реферальные выплаты для лотереи
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute(""" 
                SELECT level, amount FROM referral_rewards
                WHERE referral_system_id = ? AND reward_type = 'lottery'
            """, (referral_system_id,))
            reward_percentages = {row[0]: row[1] for row in cursor.fetchall()}  # {1: 50, 2: 30, 3: 20}

        # Переходим по уровням и начисляем бонусы
        for level in range(current_user_level, 0, -1):
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT referrer_id FROM referrals WHERE referred_id = ? AND level = ?
                """, (current_user_id, level))
                referrer = cursor.fetchone()

            if not referrer or not referrer[0]:
                break

            referrer_id = referrer[0]
            reward_percentage = reward_percentages.get(level, 0)

            if reward_percentage > 0:
                reward_amount = (prize_amount * reward_percentage) / 100
                add_referral_reward(referrer_id, reward_amount)

                # Уведомляем пригласившего пользователя
                try:
                    referrer_language = await get_user_language(referrer_id)
                    message_text = (
                        f"🎉 Вы получили {reward_amount} VED за выигрыш вашего реферала в лотерее!"
                        if referrer_language == "ru" else
                        f"🎉 You received {reward_amount} VED for your referral's lottery win!"
                    )
                    await message.bot.send_message(referrer_id, message_text)
                except Exception as e:
                    logging.error(f"Ошибка при отправке уведомления рефереру {referrer_id}: {e}")

            # Переход на следующий уровень
            current_user_id = referrer_id

    # Завершаем лотерею
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE lottery SET active = 0 WHERE id = ?", (lottery_id,))
        conn.commit()

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lottery_tickets WHERE lottery_id = ?", (lottery_id,))
        conn.commit()

    await message.reply("Лотерея завершена. Победители и участники с утешительными призами уведомлены.")

async def assign_prizes_to_tickets(lottery_id, total_tickets_count, consolation_prize="Утешительный приз", empty_prize="Пустой"):
    # Расчёт количества выигрышных билетов
    winning_tickets_count = 54  # 54 выигрышных билета
    winner_percentage = (total_tickets_count // 2) - winning_tickets_count  # половина от общего количества минус 54

    # Определение категорий призов для выигрышных билетов
    winning_categories = ['10%'] * 9 + ['1%'] * 9 + ['0.1%'] * 9 + ['0.01%'] * 9 + ['0.001%'] * 9 + ['0.0001%'] * 9
    random.shuffle(winning_categories)

    # Генерация списка всех билетов с присвоением призов
    tickets = []
    consolation_count = 0
    for ticket_number in range(1, total_tickets_count + 1):
        user_id = get_user_id_for_ticket(ticket_number)  # Получаем user_id для билета (замени на свою логику)
        username = get_username_by_user_id_for_admin(user_id)  # Получаем username по user_id (замени на свою логику)

        if ticket_number <= winning_tickets_count:
            prize = winning_categories.pop()  # Присваиваем выигрышные категории
            tickets.append((lottery_id, user_id, username, ticket_number, 1, prize))  # Добавляем выигрышный билет
        elif consolation_count < winner_percentage:  # Утешительные билеты
            tickets.append((lottery_id, user_id, username, ticket_number, 0, consolation_prize))
            consolation_count += 1
        else:  # Пустые билеты
            tickets.append((lottery_id, user_id, username, ticket_number, 0, empty_prize))

    # Вставка сгенерированных билетов в базу данных
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO lottery_tickets (lottery_id, user_id, username, ticket_number, is_winner, prize) VALUES (?, ?, ?, ?, ?, ?)",
            tickets
        )
        conn.commit()

    # Логирование
    for ticket in tickets:
        lottery_id, user_id, username, ticket_number, is_winner, prize = ticket
        if user_id is None:
            # Если user_id равен None, логируем ошибку
            logging.error(f"Ошибка: билет {ticket_number} имеет user_id=None")
        else:
            logging.info(f"Билет {ticket_number} | Пользователь ID: {user_id} | Номер билета: {ticket_number}")

def calculate_prize(prize_fund, prize_category):
    """Функция для расчета выигрыша по категории с логированием."""
    percentages = {
        '10%': 0.10,
        '1%': 0.01,
        '0.1%': 0.001,
        '0.01%': 0.0001,
        '0.001%': 0.00001,
        '0.0001%': 0.000001
    }
    calculated_prize = round(prize_fund * percentages.get(prize_category, 0), 6)

    logging.info(f"Расчёт приза: {prize_category} от {prize_fund} VED = {calculated_prize} VED")

    return calculated_prize


@router.message(lambda message: message.text and message.text.strip() in {str(texts['view_lottery_participants'].get(lang, '') or '').strip() for lang in texts['view_lottery_participants']})
async def view_lottery_participants(message: types.Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ticket_number, username, user_id FROM lottery_tickets WHERE user_id IS NOT NULL"
        )
        participants = cursor.fetchall()
    if participants:
        response = "\n".join([f"Билет #{ticket[0]}: @{ticket[1]} (ID: {ticket[2]})" for ticket in participants])
    else:
        response = "Участников пока нет."
    await message.reply(response)

class TicketPriceState(StatesGroup):
    waiting_for_price = State()

@router.message(lambda message: message.text and message.text.strip() in {str(texts['set_lottery_ticket_price'].get(lang, '') or '').strip() for lang in texts['set_lottery_ticket_price']})
async def set_ticket_price(message: types.Message, state: FSMContext):
    await message.reply(
        "Введите цену за билет (целое число):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(TicketPriceState.waiting_for_price)

@router.message(TicketPriceState.waiting_for_price)
async def process_ticket_price(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError("Некорректная цена.")

        # Обновляем цену билета в базе данных
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE lottery SET ticket_price = ? WHERE active = 1", (price,))
            conn.commit()

        await message.reply(f"Цена за билет успешно установлена: {price} VED.")
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите корректную цену (целое число больше нуля):")

@router.message(lambda message: message.text and message.text.strip() in {str(texts['file_command'].get(lang, '') or '').strip() for lang in texts['file_command']})
async def send_file(message: types.Message):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    if os.path.exists(FILE_PATH):
        # Открываем файл в бинарном режиме
        with open(FILE_PATH, 'rb') as file:
            # Передаем файл как BufferedInputFile
            input_file = BufferedInputFile(file.read(), filename="texts.xlsx")  # Передаем байтовый поток
            await message.bot.send_document(message.chat.id, input_file)
    else:
        await message.answer("Файл с командами не найден.")


@router.message(lambda message: message.text and message.text.strip() in {str(texts['new_file_command'].get(lang, '') or '').strip() for lang in texts['new_file_command']})
async def new_file_command(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    await message.answer("Пожалуйста, отправьте файл в формате .xlsx.")
    # Устанавливаем состояние с использованием await state.set_state()
    await state.set_state(FileUpdateState.waiting_for_file)


@router.message(FileUpdateState.waiting_for_file)
async def update_file(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_process(message, state)
        return
    if message.document and message.document.mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        # Проверяем, существует ли файл, перед его удалением
        if os.path.exists(FILE_PATH):
            os.remove(FILE_PATH)

        # Загружаем новый файл
        new_file = await message.bot.get_file(message.document.file_id)
        await message.bot.download_file(new_file.file_path, FILE_PATH)

        await message.answer("Файл с командами обновлён.")
        await state.clear()
    else:
        await message.answer("Пожалуйста, отправьте файл в формате .xlsx.")




# Команда для запуска рассылки (только для админов)
@router.message(lambda message: message.text and message.text.strip() in {str(texts['broadcast_for_all_users'].get(lang, '') or '').strip() for lang in texts['broadcast_for_all_users']})
async def start_broadcast(message: types.Message, state: FSMContext):
    ADMINS = get_admins()
    if message.from_user.id not in ADMINS:
        return await message.answer("У вас нет прав для выполнения этой команды.")

    await state.set_state(BroadcastStateForAdminAllUsers.waiting_for_message)
    await message.answer("Введите сообщение для рассылки:")


# Обработчик ввода сообщения и отправки его всем пользователям
@router.message(BroadcastStateForAdminAllUsers.waiting_for_message)
async def send_broadcast(message: types.Message, state: FSMContext, bot):
    await state.clear()  # Сбрасываем состояние
    users = get_all_users()  # Получаем всех пользователей

    success_count = 0
    for user in users:
        try:
            await bot.send_message(user["user_id"], message.text)
            success_count += 1
        except Exception as e:
            print(f"Ошибка отправки пользователю {user['user_id']}: {e}")

    await message.answer(f"Рассылка завершена! Сообщение отправлено {hbold(success_count)} пользователям.")