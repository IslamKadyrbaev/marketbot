import logging
import sqlite3
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect('orders.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        name TEXT,
        address TEXT,
        description TEXT,
        status TEXT DEFAULT 'Заказ принят'
    )
''')
conn.commit()

class OrderForm(StatesGroup):
    category = State()
    name = State()
    address = State()
    description = State()

categories_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Еда", callback_data="food")],
    [InlineKeyboardButton(text="Запчасти", callback_data="parts")],
    [InlineKeyboardButton(text="Мебель", callback_data="furniture")],
])

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Выберите категорию заказа:", reply_markup=categories_keyboard)
    await state.set_state(OrderForm.category)

@dp.callback_query(OrderForm.category)
async def category_chosen(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(category=callback.data)
    await callback.message.answer("Введите ваше имя:")
    await state.set_state(OrderForm.name)
    await callback.answer()

@dp.message(OrderForm.name)
async def name_entered(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите адрес доставки:")
    await state.set_state(OrderForm.address)

@dp.message(OrderForm.address)
async def address_entered(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Введите дополнительную информацию о заказе (например, что именно заказать):")
    await state.set_state(OrderForm.description)

@dp.message(OrderForm.description)
async def description_entered(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    data = await state.get_data()

    cursor.execute("INSERT INTO orders (category, name, address, description) VALUES (?, ?, ?, ?)",
                   (data['category'], data['name'], data['address'], data['description']))
    conn.commit()
    order_id = cursor.lastrowid

    await message.answer(f"Заказ принят! Номер вашего заказа: {order_id}")
    await state.finish()

@dp.message(F.text.startswith('/status'))
async def check_status(message: types.Message):
    try:
        order_id = int(message.text.split()[1])
        cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        result = cursor.fetchone()
        if result:
            status = result[0]
            await message.answer(f"Статус заказа №{order_id}: {status}")
        else:
            await message.answer("Заказ с таким номером не найден.")
    except (ValueError, IndexError):
        await message.answer("Неверный формат команды. Используйте /status <номер заказа>")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())