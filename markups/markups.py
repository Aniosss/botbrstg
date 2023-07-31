import re

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils.processing import get_list_of_terms, get_list_of_subj

btn_all_grades = KeyboardButton('Все оценки')
btn_term_grades = KeyboardButton('Оценки за семестр')
btn_subj_grades = KeyboardButton('Оценки по предмету')
btn_att_grades = KeyboardButton('Оценки за аттестацию')
btn_final_grades = KeyboardButton('Итоговые оценки')
btn_unlogin = KeyboardButton('Выйти из профиля')
btn_update = KeyboardButton('Обновить оценки')

main_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
main_menu.add(btn_att_grades, btn_subj_grades, btn_term_grades, btn_final_grades, btn_all_grades,btn_update, btn_unlogin)


def create_att_select(term: str):
    att_select = {"inline_keyboard":
        [
            [{'text': '1', 'callback_data': '1_' + term}],
            [{'text': '2', 'callback_data': '2_' + term}],
            [{'text': '3', 'callback_data': '3_' + term}]
        ]
    }
    return att_select


def clean_callback_value(value):
    # Удаляем пробелы и знаки подчеркивания, заменяя их на "-"
    return re.sub(r'[\s_]', '.', value)


def create_inline_of_terms(grades):
    keyboard = InlineKeyboardMarkup(row_width=2)
    data = []
    terms = get_list_of_terms(grades)

    for term in terms:
        data.append({
            'text': term,
            'callback': 'semester_' + term
        })

    for item in data:
        button = InlineKeyboardButton(text=item['text'], callback_data=item['callback'])
        keyboard.insert(button)

    return keyboard


def create_inline_of_subj(grades, term):
    keyboard = InlineKeyboardMarkup(row_width=1)
    data = []
    subj = get_list_of_subj(grades, term)

    for sub in subj:
        data.append({
            'text': sub,
            'callback': 'sub_' + clean_callback_value(sub)[:30] + '_' + clean_callback_value(term)
        })

    for item in data:
        button = InlineKeyboardButton(text=item['text'], callback_data=item['callback'])
        keyboard.insert(button)

    return keyboard
