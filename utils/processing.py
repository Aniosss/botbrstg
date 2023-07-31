import pandas as pd
import requests
import numpy as np
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from json import dumps, loads

from cryptography.fernet import Fernet


def get_grades(login: str, password: str):
    # Данные для авторизации
    data = {  # fill
        "login": login,
        "password": password,
        "user_type": '',
        "button_login": "%D0%92%D1%85%D0%BE%D0%B4"
    }
    # URL-адрес сайта и путь к странице аутентификации
    base_url = "https://www.cs.vsu.ru/brs"
    login_url = base_url + "/login"

    # Создаем сессию для сохранения куков
    session = requests.Session()

    response = session.get(base_url)
    # Отправляем POST-запрос для аутентификации
    response = session.post(login_url, data=data)
    if response.status_code == 200 and len(response.url.split('/')) == 6:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Находим таблицу с оценками
        table = soup.select_one('table.table-bordered')

        rows_data = []
        for cur_row in table.find_all('tr'):
            cells = cur_row.find_all('td')
            cells_th = cur_row.find_all('th')

            if len(cells_th) > 1:
                cur_row_data = [cell.get_text().strip() for cell in cells_th]
            else:
                cur_row_data = [cell.get_text().strip() for cell in cells]
                cur_row_data.append(cells_th[0].get_text().strip())

            rows_data.append(cur_row_data)

        return rows_data

    elif response.status_code == 503:
        return 'Error connection'
    else:
        return "Error"


def get_all_grades_of_term(grades, term: str, user_id: str):
    cur_df = grades[grades['Семестр'] == term]
    cur_df = cur_df[['Предмет', 'Отчётность', 'Преподаватель', '1', '2', '3', 'взеш. балл', 'Экзамен', 'Доп. балл',
                     'Итог. балл', 'Итог']]
    df_to_png(cur_df, user_id)


def get_grades_of_one_subject(grades, term: str, subject: str):
    cur_df = grades[(grades['Семестр'] == term) & (grades['Предмет'].str.contains(subject, regex=False))]
    cur_df = cur_df[['1', '2', '3', 'взеш. балл', 'Экзамен', 'Доп. балл',
                     'Итог. балл', 'Итог']]
    return cur_df


def get_grades_of_one_att(grades, term: str, att: str):
    cur_df = grades[grades['Семестр'] == term]
    return cur_df[['Предмет', att]]


def get_final_grades_of_term(grades, term: str):
    cur_df = grades[grades['Семестр'] == term]
    return cur_df[['Предмет', 'Итог. балл', 'Итог']]


def get_all_grades(df, user_id: str):
    df_to_png(df, user_id)


def get_list_of_terms(df):
    return sorted(df['Семестр'].unique())


def get_list_of_subj(df, term: str):
    return list(df[df['Семестр'] == term]['Предмет'].unique())


def list_to_df(lst):
    df = pd.DataFrame(lst[1:], columns=lst[0])
    df['Предмет'] = df['Предмет'].str.split('(').str[0]
    return df


def get_name_of_cols(df):
    return list(df)


def df_to_png(df, user_id: str):
    plt.style.use('ggplot')

    fig, ax = plt.subplots(figsize=(24, 1))  # Изменение высоты графика
    ax.axis('off')  # Отключение отображения осей
    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center')

    # Настройка ширины столбцов
    num_columns = len(df.columns)
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    for i in range(num_columns):
        column_width = max([len(str(value)) for value in df.iloc[:, i]] + [len(df.columns[i])])
        table.auto_set_column_width(col=i)

    plt.savefig('files/' + user_id + '_table.png', bbox_inches='tight')


def list_to_str(lst: list):
    # Преобразовываем все строки в Unicode
    lst_unicode = [str(item) for item in lst]
    list_str = dumps(lst_unicode, ensure_ascii=False)
    return list_str


def str_to_list(s: str):
    data = loads(s)
    return data


# Шифруем пароль с помощью ключа
def encrypt_password(password, key):
    cipher_suite = Fernet(key)
    encrypted_password = cipher_suite.encrypt(password.encode())
    return encrypted_password


# Расшифровываем пароль с помощью ключа
def decrypt_password(encrypted_password, key):
    cipher_suite = Fernet(key)
    decrypted_password = cipher_suite.decrypt(encrypted_password).decode()
    return decrypted_password
