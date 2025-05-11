import asyncio
from supabase_client import supabase
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

TOKEN = "7742271833:AAHSLAIQyOAQ_D_z3dzigzIR0Yp-qxeQhBI"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Состояния формы
class Form(StatesGroup):
    product = State()
    price = State()
    region = State()
    photo = State()
    contact = State()
    confirm = State()

# Главное меню
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Подать объявление")],
            [KeyboardButton(text="Посмотреть товары")],
            [KeyboardButton(text="Поиск по слову")],
            [KeyboardButton(text="Справка")]
        ],
        resize_keyboard=True
    )
    await message.answer("Привет! Выберите действие:", reply_markup=keyboard)

# Справка
@dp.message(F.text == "Справка")
async def help_section(message: Message):
    await message.answer("Этот бот помогает продавать и покупать свежие ягоды, овощи и фрукты по всей России. Подать объявление можно в пару кликов!")

# Заглушка: Посмотреть товары
@dp.message(F.text == "Посмотреть товары")
async def show_items(message: Message):
    await message.answer("Пока товаров нет. Но скоро они появятся!")

# Заглушка: Поиск по слову
@dp.message(F.text == "Поиск по слову")
async def search_items(message: Message):
    await message.answer("Функция поиска в разработке. Совсем скоро!")

# Начало подачи объявления
@dp.message(F.text == "Подать объявление")
async def start_ad_form(message: Message, state: FSMContext):
    await message.answer("Что вы хотите продать?")
    await state.set_state(Form.product)

@dp.message(Form.product)
async def get_product(message: Message, state: FSMContext):
    await state.update_data(product=message.text)
    await message.answer("Сколько и по какой цене?")
    await state.set_state(Form.price)

@dp.message(Form.price)
async def get_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Из какого вы района?")
    await state.set_state(Form.region)

@dp.message(Form.region)
async def get_region(message: Message, state: FSMContext):
    await state.update_data(region=message.text)
    await message.answer("Пришлите, пожалуйста, фото товара.")
    await state.set_state(Form.photo)

@dp.message(Form.photo, F.photo)
async def get_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer("Как с вами связаться? Напишите телефон, Telegram или WhatsApp.")
    await state.set_state(Form.contact)

@dp.message(Form.contact)
async def get_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    data = await state.get_data()

    # Кнопки подтверждения
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data="confirm_publish")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_publish")]
    ])

    # Покажем предпросмотр
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=data['photo'],
        caption=(
            "<b>Проверьте объявление:</b>\n\n"
            f"<b>Товар:</b> {data['product']}\n"
            f"<b>Цена:</b> {data['price']}\n"
            f"<b>Район:</b> {data['region']}\n"
            f"<b>Контакт:</b> {data['contact']}\n\n"
            "Опубликовать в канал?"
        ),
        reply_markup=confirm_kb,
        parse_mode=ParseMode.HTML
    )

    await state.set_state(Form.confirm)

@dp.callback_query(F.data == "confirm_publish")
async def confirm_publish(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

# Сохраняем объявление в базу Supabase
    supabase.table("announcements").insert({
    "product": data["product"],
    "price": data["price"],
    "region": data["region"],
    "contact": data["contact"],
    "photo_id": data["photo"]
}).execute()

    await callback.message.edit_caption("<b>✅ Объявление опубликовано!</b>", parse_mode=ParseMode.HTML)
    await bot.send_photo(
        chat_id='@klyukvamarket',
        photo=data['photo'],
        caption=(
            f"<b>Товар:</b> {data['product']}\n"
            f"<b>Цена:</b> {data['price']}\n"
            f"<b>Район:</b> {data['region']}\n"
            f"<b>Контакт:</b> {data['contact']}"
        ),
        parse_mode=ParseMode.HTML
    )

    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "cancel_publish")
async def cancel_publish(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_caption("<b>❌ Объявление отменено.</b>", parse_mode=ParseMode.HTML)
    await state.clear()
    await callback.answer()


@dp.message(Command("поиск"))
async def search_command(message: Message):
    query = message.text.split(maxsplit=1)

    if len(query) < 2:
        await message.answer("Пожалуйста, укажите слово для поиска. Пример:\n/поиск клубника\n/поиск 100\n/поиск Красногорск")
        return

    keyword = query[1].lower()

    response = supabase.table("announcements").select("*").execute()
    results = response.data

    matches = [
        item for item in results
        if keyword in item['product'].lower()
        or keyword in item['region'].lower()
        or keyword in item['price'].lower()
    ]

    if not matches:
        await message.answer("Ничего не найдено.")
        return

    for item in matches:
        caption = (
            f"<b>Товар:</b> {item['product']}\n"
            f"<b>Цена:</b> {item['price']}\n"
            f"<b>Район:</b> {item['region']}\n"
            f"<b>Контакт:</b> {item['contact']}"
        )
        await bot.send_photo(message.chat.id, item["photo_id"], caption=caption, parse_mode=ParseMode.HTML)


@dp.message(Command("все"))
async def show_all_command(message: Message):
    response = supabase.table("announcements").select("*").order("created_at", desc=True).limit(5).execute()
    results = response.data

    if not results:
        await message.answer("Объявлений пока нет.")
        return

    for item in results:
        caption = (
            f"<b>Товар:</b> {item['product']}\n"
            f"<b>Цена:</b> {item['price']}\n"
            f"<b>Район:</b> {item['region']}\n"
            f"<b>Контакт:</b> {item['contact']}"
        )
        await bot.send_photo(message.chat.id, item["photo_id"], caption=caption, parse_mode=ParseMode.HTML)

@dp.message(Command("дешевле"))
async def cheaper_than(message: Message):
    query = message.text.split(maxsplit=1)
    if len(query) < 2 or not query[1].isdigit():
        await message.answer("Укажите число. Пример: /дешевле 150")
        return

    max_price = int(query[1])
    response = supabase.table("announcements").select("*").execute()
    results = response.data

    matches = []
    for item in results:
        try:
            price = int(''.join(filter(str.isdigit, item['price'])))
            if price <= max_price:
                matches.append(item)
        except:
            continue

    if not matches:
        await message.answer("Объявлений по такой цене не найдено.")
        return

    for item in matches:
        caption = (
            f"<b>Товар:</b> {item['product']}\n"
            f"<b>Цена:</b> {item['price']}\n"
            f"<b>Район:</b> {item['region']}\n"
            f"<b>Контакт:</b> {item['contact']}"
        )
        await bot.send_photo(message.chat.id, item["photo_id"], caption=caption, parse_mode=ParseMode.HTML)


@dp.message(Command("дороже"))
async def more_than(message: Message):
    query = message.text.split(maxsplit=1)
    if len(query) < 2 or not query[1].isdigit():
        await message.answer("Укажите число. Пример: /дороже 300")
        return

    min_price = int(query[1])
    response = supabase.table("announcements").select("*").execute()
    results = response.data

    matches = []
    for item in results:
        try:
            price = int(''.join(filter(str.isdigit, item['price'])))
            if price >= min_price:
                matches.append(item)
        except:
            continue

    if not matches:
        await message.answer("Объявлений по такой цене не найдено.")
        return

    for item in matches:
        caption = (
            f"<b>Товар:</b> {item['product']}\n"
            f"<b>Цена:</b> {item['price']}\n"
            f"<b>Район:</b> {item['region']}\n"
            f"<b>Контакт:</b> {item['contact']}"
        )
        await bot.send_photo(message.chat.id, item["photo_id"], caption=caption, parse_mode=ParseMode.HTML)

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())