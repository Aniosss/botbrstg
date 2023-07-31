import redis

client = redis.Redis(host='localhost', port=6379, db=0)
lst = ['Все оценки', 'Оценки за семестр', 'Оценки по предмету', 'Оценки за аттестацию', 'Итоговые оценки',
       'Выйти из профиля', 'Обновить оценки']


def add_to_all():
    cmd = 'Все оценки'
    cur_value = client.get(cmd)
    client.set(cmd, int(cur_value) + 1)


def add_to_term():
    cmd = 'Оценки за семестр'
    cur_value = client.get(cmd)
    client.set(cmd, int(cur_value) + 1)


def add_to_subj():
    cmd = 'Оценки по предмету'
    cur_value = client.get(cmd)
    client.set(cmd, int(cur_value) + 1)


def add_to_final():
    cmd = 'Итоговые оценки'
    cur_value = client.get(cmd)
    client.set(cmd, int(cur_value) + 1)


def add_to_att():
    cmd = 'Оценки за аттестацию'
    cur_value = client.get(cmd)
    client.set(cmd, int(cur_value) + 1)


def add_to_exit():
    cmd = 'Выйти из профиля'
    cur_value = client.get(cmd)
    client.set(cmd, int(cur_value) + 1)


def add_to_refresh():
    cmd = 'Обновить оценки'
    cur_value = client.get(cmd)
    client.set(cmd, int(cur_value) + 1)


def add_uniq_user(user_id):
    client.sadd('uniq_users', user_id)


def get_cnt_uniq():
    client.scard('uniq_users')
