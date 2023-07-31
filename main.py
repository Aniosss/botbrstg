import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InputFile
from aiogram.types import ParseMode
import prettytable as pt

from database.db import create_table, create_connection, User, insert_values, is_record_exists
from markups import markups as nav
from utils import processing
from database import db, redis_cnt

from dotenv import load_dotenv
import os

from utils.processing import list_to_df

TABLE_NAME = 'users'
ADMIN_ID = 712482010

load_dotenv()
bot = Bot(os.getenv('TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

conn = create_connection()
create_table(conn)
conn.close()


class LoginForm(StatesGroup):
    login = State()  # Состояние для ввода логина
    password = State()  # Состояние для ввода пароля


class SelectForm(StatesGroup):
    term_state = State()  # Состояние для ввода оценок по семестру
    subj_state = State()  # Состояние для ввода оценок по предмету
    att_state = State()  # Состояние для ввода оценок по атте
    finish_state = State()  # Состояние для ввода итоговых оценок


# Функция для автообновления данных в БД
async def update_data(user_id):
    con = db.create_connection()

    login, password = db.get_data_user(con, user_id, TABLE_NAME)

    grades = processing.get_grades(login, password)
    if grades != "Error" and grades != "Error connection":
        grades = processing.list_to_str(grades)
        db.update_user_grades(con, user_id, grades)

    con.close()


async def auto_update_all_data():
    while True:
        await asyncio.sleep(43200)  # Обновление данных каждый 12 часов

        con = db.create_connection()
        list_of_users = db.get_all_user_ids(con)
        con.close()

        for i in list_of_users:
            await update_data(i)


async def on_startup(dp):
    asyncio.create_task(auto_update_all_data())
    await bot.send_message(chat_id=ADMIN_ID, text='Bot has been started')


async def on_shutdown(_):
    await bot.send_message(chat_id=ADMIN_ID, text='Bot has been stopped')


@dp.message_handler(commands=['start'], state='*')
async def start_handler(message: types.Message, state: FSMContext):
    await send_home(message, state)


async def send_home(message, state):
    await state.finish()
    conn = create_connection()
    if not is_record_exists(conn, TABLE_NAME, message.from_user.id):
        await message.answer("Введите логин:")

        # Устанавливаем состояние для ввода логина
        await LoginForm.login.set()
    else:
        await message.answer('Выберите дальнейшее действие:', reply_markup=nav.main_menu)


@dp.message_handler(state=LoginForm.login)
async def login_handler(message: types.Message, state: FSMContext):
    login = message.text
    lst = ['Все оценки', 'Оценки за семестр', 'Оценки по предмету', 'Оценки за аттестацию', 'Итоговые оценки',
           'Выйти из профиля', 'Обновить оценки']

    if login in lst:
        await start_handler(message, state)
        await state.finish()
    else:
        # Сохраняем логин в контексте состояния
        await state.update_data(login=login)

        await message.reply("Введите пароль:")

        # Устанавливаем состояние для ввода пароля
        await LoginForm.password.set()


@dp.message_handler(state=LoginForm.password)
async def password_handler(message: types.Message, state: FSMContext):
    password = message.text

    # Получаем логин из контекста состояния
    data = await state.get_data()
    login = data.get('login')
    await message.answer('Идет авторизация, ожидайте.')
    grades = processing.get_grades(login, password)

    # Проверяем правильность пароля
    if grades == "Error":
        await message.reply("Неверный пароль. Попробуйте еще раз.\nВведите логин:")
        await LoginForm.login.set()
    elif grades == "Error connection":
        await message.reply("Сайт лежит. Попробуйте позже.\nВведите логин:")
        await LoginForm.login.set()
    else:
        grades = processing.list_to_str(grades)
        conn = create_connection()
        user = User(message.from_user.id, login, password, grades, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        insert_values(conn, user)
        conn.close()
        redis_cnt.add_uniq_user(message.from_user.id)
        await message.reply("Вход выполнен успешно! Выберите дальнейшее действие:", reply_markup=nav.main_menu)
        # Сбрасываем состояния
        await state.finish()


@dp.message_handler(lambda message: message.text == 'Оценки по предмету')
async def bot_message(message: types.Message):
    redis_cnt.add_to_subj()
    conn = create_connection()
    data = db.get_grades_db(conn, message.from_user.id)
    grades = list_to_df(data)
    conn.close()

    keyboard = nav.create_inline_of_terms(grades)
    await SelectForm.subj_state.set()
    await message.answer('Выберите семестр', reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith='semester_'), state=SelectForm.subj_state)
async def callback_subj(call: types.CallbackQuery):
    con = create_connection()
    data = db.get_grades_db(con, call.from_user.id)
    con.close()
    grades = list_to_df(data)

    term = call.data.split('_')[1]
    keyboard = nav.create_inline_of_subj(grades, term)
    await call.message.answer('Выберите предмет', reply_markup=keyboard)
    await call.answer()


@dp.callback_query_handler(Text(startswith='sub'), state=SelectForm.subj_state)
async def callback_sub(call: types.CallbackQuery, state: FSMContext):
    con = create_connection()
    data = db.get_grades_db(con, call.from_user.id)
    con.close()
    grades = list_to_df(data)

    sub = ' '.join(call.data.split('_')[1].split('.'))
    term = call.data.split('_')[2]

    table = pt.PrettyTable(['Колонка', 'Оценка'])
    table.align['Колонка'] = 'l'

    df = processing.get_grades_of_one_subject(grades, term, sub)
    df_melted = df.melt(value_vars=df.columns)

    for kln, grd in df_melted.values:
        table.add_row([kln, grd])

    await call.message.answer(f'Оценки по предмету {term} семестра - "{sub[:-1]}":')
    await call.message.reply(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML, reply_markup=nav.main_menu)
    await state.finish()
    await call.answer()


@dp.message_handler(lambda message: message.text == 'Оценки за семестр')
async def bot_message(message: types.Message):
    redis_cnt.add_to_term()
    conn = create_connection()
    data = db.get_grades_db(conn, message.from_user.id)
    grades = list_to_df(data)
    conn.close()

    keyboard = nav.create_inline_of_terms(grades)
    await SelectForm.term_state.set()
    await message.answer('Выберите семестр', reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith='semester_'), state=SelectForm.term_state)
async def term(call: types.CallbackQuery, state: FSMContext):
    con = create_connection()
    data = db.get_grades_db(con, call.from_user.id)
    con.close()
    grades = list_to_df(data)

    await call.message.answer('Идет обработка запроса...')
    term = call.data.split('_')[1]
    processing.get_all_grades_of_term(grades, term, str(call.from_user.id))
    path = f'files/{call.from_user.id}_table.png'
    photo = InputFile(path)
    await bot.send_photo(chat_id=call.message.chat.id, photo=photo, reply_markup=nav.main_menu)

    os.remove(path)
    await state.finish()
    await call.answer()


@dp.message_handler(lambda message: message.text == 'Оценки за аттестацию')
async def bot_message(message: types.Message):
    redis_cnt.add_to_att()
    conn = create_connection()
    data = db.get_grades_db(conn, message.from_user.id)
    grades = list_to_df(data)
    conn.close()

    keyboard = nav.create_inline_of_terms(grades)
    await SelectForm.att_state.set()
    await message.answer('Выберите семестр', reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith='semester_'), state=SelectForm.att_state)
async def callback_atts(call: types.CallbackQuery):
    term = call.data.split('_')[1]
    keyboard = nav.create_att_select(term)
    await call.message.answer('Выберите аттестацию', reply_markup=keyboard)
    await call.answer()


@dp.callback_query_handler(state=SelectForm.att_state)
async def callback_att(call: types.CallbackQuery, state: FSMContext):
    att, term = call.data.split('_')
    con = create_connection()
    grades = list_to_df(db.get_grades_db(con, call.from_user.id))
    con.close()

    grade = processing.get_grades_of_one_att(grades, term, att)

    table = pt.PrettyTable(['Предмет', 'Оценка'])
    table.align['Предмет'] = 'l'

    data = []
    for i in grade.values:
        data.append((i[0][:36 - 15], i[1]))

    for subj, grd in data:
        table.add_row([subj, grd])

    await call.message.answer(f'Оценки за {att} аттестацию {term} семестра:')
    await call.message.answer(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML, reply_markup=nav.main_menu)

    await state.finish()
    await call.answer()


@dp.message_handler(lambda message: message.text == 'Итоговые оценки')
async def bot_message(message: types.Message):
    redis_cnt.add_to_final()
    conn = create_connection()
    data = db.get_grades_db(conn, message.from_user.id)
    grades = list_to_df(data)
    conn.close()

    keyboard = nav.create_inline_of_terms(grades)
    await SelectForm.finish_state.set()
    await message.answer('Выберите семестр', reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith='semester_'), state=SelectForm.finish_state)
async def callback_atts(call: types.CallbackQuery, state: FSMContext):
    term = call.data.split('_')[1]
    conn = create_connection()
    data = db.get_grades_db(conn, call.from_user.id)
    grades = list_to_df(data)
    conn.close()

    table = pt.PrettyTable(['Предмет', 'Оценка'])
    table.align['Предмет'] = 'l'

    grades = processing.get_final_grades_of_term(grades, term)
    data = []
    for i in grades.values:
        data.append((i[0][:36 - 15], i[1]))

    for subj, grd in data:
        table.add_row([subj, grd])

    await call.message.answer(f'Свод итоговых оценок {term} семестра:')
    await call.message.answer(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML, reply_markup=nav.main_menu)

    await state.finish()
    await call.answer()


@dp.message_handler(lambda message: message.text == 'Все оценки')
async def bot_message(message: types.Message):
    redis_cnt.add_to_all()
    conn = create_connection()
    data = db.get_grades_db(conn, message.from_user.id)
    grades = list_to_df(data)
    conn.close()

    await message.answer('Идет обработка запроса...')
    processing.get_all_grades(grades, str(message.from_user.id))
    path = f'files/{message.from_user.id}_table.png'
    photo = InputFile(path)
    await bot.send_photo(chat_id=message.chat.id, photo=photo, reply_markup=nav.main_menu)

    os.remove(path)


@dp.message_handler(lambda message: message.text == 'Обновить оценки')
async def bot_message(message: types.Message):
    redis_cnt.add_to_refresh()
    con = create_connection()
    login, password = db.get_data_user(con, message.from_user.id, TABLE_NAME)
    await message.answer('Идет обработка запроса...')
    grades = processing.get_grades(login, password)

    if grades != "Error" and grades != "Error connection":
        grades = processing.list_to_str(grades)
        db.update_user_grades(con, message.from_user.id, grades)
        await message.answer('Оценки успешно обновлены!', reply_markup=nav.main_menu)
    elif grades == "Error":
        await message.answer(
            "Ваши данные были изменены, авторизуйтесь заново.")  # в случае обновления пароля пользователем
        db.remove_user(con, TABLE_NAME, message.from_user.id)
        await start_handler(message)
    else:
        await message.answer('Сайт лежит, обновление оценок невозможно, попробуйте позже.')

    con.close()


@dp.message_handler(lambda message: message.text == 'Выйти из профиля')
async def bot_message(message: types.Message, state: FSMContext):
    redis_cnt.add_to_exit()
    conn = create_connection()
    db.remove_user(conn, TABLE_NAME, message.from_user.id)
    conn.close()

    await start_handler(message, state)


if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)
