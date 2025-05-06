import random
import telebot
import os
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import EnglWord, EnglWordUser, User, Base
from telebot import types, TeleBot
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
import sqlalchemy as sq
from dotenv import load_dotenv

load_dotenv() 

state_storage = StateMemoryStorage()

# задаем параметры токена для подключения бота через переменную окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment variables.")
bot = TeleBot(BOT_TOKEN, state_storage=state_storage)

# задаем параметры базы данных для подключения через переменные окружения
DB_USER = os.getenv('DB_USER', '')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', '')

# подключение к базе данных
DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = sqlalchemy.create_engine(DSN)
Session = sessionmaker(bind=engine)
session = Session()

def create_db_word():
    # удаление таблицы если надо
    #Base.metadata.drop_all(engine)
    # создание таблиц в базе данных
    Base.metadata.create_all(engine)

    # Проверяем, есть ли уже слова в таблице
    if session.query(EnglWord).count() == 0:
        words_list = [
            ['Звезда', 'Star'], ['Солнце', 'Sun'],
            ['Планета', 'Planet'], ['Звездный путь', 'Star trek'],
            ['Небо', 'Sky'], ['Луна', 'Moon'],
            ['Земля', 'Earth'], ['Космос', 'Space'],
            ['Комета', 'Comet'], ['Метеор', 'Meteor']
        ]

        for word in words_list:
            session.add(EnglWord(russian_word=word[0], target_word=word[1]))
        session.commit()

        print('Словарь создан:')
        for word in session.query(EnglWord).all():
            print(word)
    else:
        print('Таблица уже содержит данные.')


def add_users(engine, chat_id):
    with Session() as session:
        user = session.query(User).filter_by(chat_id=chat_id).first()
        if not user:
            session.add(User(chat_id=chat_id))
            session.commit()
            print(f"Новый пользователь добавлен: {chat_id}")
        else:
            print(f"Пользователь уже существует: {chat_id}")

def add_words(engine, chat_id, russian_word, target_word):
    user_id = session.query(User.id).filter(User.chat_id == chat_id).first()[0]
    session.add(EnglWordUser(russian_word=russian_word, target_word=target_word, user_id=user_id))
    session.commit()

def delete_words(engine, chat_id, russian_word):
    user_id = session.query(User.id).filter(User.chat_id == chat_id).first()[0]
    session.query(EnglWordUser).filter(EnglWordUser.user_id == user_id, 
                                       EnglWordUser.russian_word == russian_word).delete()
    session.commit()

userStep = {}
buttons = []

def get_words(engine, user_id):
    words = session.query(EnglWordUser.russian_word, EnglWordUser.target_word) \
        .join(User, User.id == EnglWordUser.user_id) \
        .filter(User.id == EnglWordUser.user_id).all()
    all_words = session.query(EnglWord.russian_word, EnglWord.target_word).all()
    result = all_words + words
    return result

def show_hint(*lines):
    return '\n'.join(lines)

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово ➖'
    NEXT = 'Дальше 🐰'

class MyStates(StatesGroup):
    target_word = State()
    russian_word = State()
    other_words = State()

def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        new_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0

@bot.message_handler(commands=['start'])
def start_bot(message):
    chat_id = message.chat.id

    add_users(engine, chat_id)  # Добавляем пользователя, если его нет

    bot.send_message(
        message.chat.id,
        f'<i>TG-bot приветствует тебя, новый пользователь в обучалке английскому языку!\n\n'
        'Ты сможешь изучать и добавлять новые слова.\n'
        'Для начала нажми</i> /learn',
        parse_mode='html'
    )

@bot.message_handler(commands=['learn'])
def go_learn_bot(message):
    chat_id = message.chat.id
    userStep[chat_id] = 0
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []

    get_word = random.sample(get_words(engine, chat_id), 4)
    target_word = get_word[0][0] # брать из БД
    translate = get_word[0][1]  # брать из БД
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    others = [word[0] for word in get_word[1:]]  # брать из БД
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)

    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    markup.add(*buttons)

    bot.send_message(message.chat.id, 
                     f'<i>Выбери перевод слова: <b>{translate}</b></i>', 
                     parse_mode= 'html', reply_markup=markup)

    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['russian_word'] = translate
        data['other_words'] = others

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_type(message):
    go_learn_bot(message)

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    chat_id = message.chat.id
    userStep[chat_id] = 1
    bot.send_message(chat_id, '<i>Введите слово на английском:</i>', parse_mode= 'html')
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    print(message.text)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    chat_id = message.chat.id
    userStep[chat_id] = 3
    bot.send_message(chat_id, '<i>Введите слово для удаления на русском:</i>', parse_mode= 'html')
    bot.set_state(message.from_user.id, MyStates.russian_word, message.chat.id)
    print(message.text)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    chat_id = message.chat.id

    if userStep[chat_id] == 0:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            target_word = data['target_word']
            if message.text == target_word:
                bot.send_message(message.chat.id, '<i>Ответ верный ✅</i>', parse_mode= 'html')
                next_btn = types.KeyboardButton(Command.NEXT)
                add_word_btn = types.KeyboardButton(Command.ADD_WORD)
                delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
                buttons.extend([next_btn, add_word_btn, delete_word_btn])
            else:
                bot.send_message(message.chat.id, '<i>Ответ не верный ❌</i>', parse_mode= 'html')
        markup.add(*buttons)
        go_learn_bot(message)

    elif userStep[chat_id] == 1:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['target_word'] = text
            bot.send_message(chat_id, '<i>Введите перевод на русском языке:</i>', parse_mode= 'html')
            bot.set_state(message.from_user.id, MyStates.russian_word, message.chat.id)
            userStep[chat_id] = 2
    
    elif userStep[chat_id] == 2:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['russian_word'] = text
            add_words(engine, chat_id, data['russian_word'], data['target_word'])
            bot.send_message(chat_id, '<i>Слово добавлено</i>', parse_mode= 'html')
            userStep[chat_id] = 0
            go_learn_bot(message)
    
    elif userStep[chat_id] == 3:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['russian_word'] = text
            delete_words(engine, message.chat.id, data['russian_word'])
            bot.send_message(message.chat.id, '<i>Слово удалено</i>', parse_mode= 'html')
            userStep[chat_id] = 0
            go_learn_bot(message)

# закрываем сессию
session.close()

if __name__ == '__main__':
    create_db_word()
    print('Start telegram bot...')
    bot.polling()