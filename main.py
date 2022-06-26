import logging
import os
import threading
import time
#from datetime import datetime, timedelta
import time
from random import randint
from contextlib import closing

import sqlite3

from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import (
    BaseFilter,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    Updater,
)

CAPTCHA_REPLY_TIMEOUT = 120  # таймаут для капчи *число* секунд
TIMEOUT_FOR_BAN = 15 # не писал *число* секунд - в бан 
DB_FILE=os.environ.get("DB_FILE", './chatbot.db')
DB_FILE_A=os.environ.get("DB_FILE_A", './useract.db')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


class FilterNewChatMembers(BaseFilter):
    """ Фильтрация сообщений о входе """

    def __init__(self):
        # Пользователи проходящие проверку капчей
        self.status_members = ["member", "restricted", "left", "kicked"]

    def __call__(self, update):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message = update.effective_message

        if message.new_chat_members:
            # Проверка, если пользователю уже давалась капча
            con = sqlite3.connect(DB_FILE, check_same_thread=False)
            with closing(con.cursor()) as cur:
                cur.execute("SELECT id FROM banlist WHERE chat_id=%s AND user_id=%s" % (chat_id, user_id))
                if cur.fetchone():
                    return False

            member_status = message.bot.getChatMember(chat_id, user_id)["status"]
            if member_status in self.status_members:
                return True
        return False
        con.close()
#-------------------------------------------------------------------------------------------
class FilterMessageMembers(BaseFilter):
    """ Фильтрация сообщений пользователей """

    def __init__(self):
        # Пользователи проходящие проверку статуса
        self.status_members = ["member","restricted","kicked"]

    def __call__(self, update):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message = update.effective_message        
        member_status = message.bot.getChatMember(chat_id, user_id)["status"]
        if member_status in self.status_members:
                    return True
        return False
#-------------------------------------------------------------------------------------------

#-------------------------------------------------------------------------------------------

def banUser():
    """
    Работает второстепенным потоком, банит
    пользователей не ответивших или ответивших
    неправильно, по истечению времени указанного в бд
    """

    while True:
        time.sleep(30)
        logger.info("30s cycle of ban thread")
        con = sqlite3.connect(DB_FILE, check_same_thread=False)
        with closing(con.cursor()) as cur:
            cur.execute(
                "SELECT id, user_id, chat_id, captcha_message_id FROM banlist WHERE time<%s" % int(time.time())
            )
            for banrecord in cur.fetchall():
                ban = {
                    "id_record": banrecord[0],
                    "user_id": banrecord[1],
                    "chat_id": banrecord[2],
                    "captcha_message_id": banrecord[3],
                }
                cur.execute("DELETE FROM banlist WHERE id=%s" % (ban["id_record"]))
                con.commit()
                con.close()
                try:
                    dispatcher.bot.ban_chat_member(
                        chat_id=ban["chat_id"], user_id=ban["user_id"]
                    )
                except Exception:
                    logger.exception(f"Can't kick user user_id={ban['user_id']}")

                # Clean up in the chat
                try:
                    dispatcher.bot.delete_message(
                        ban["chat_id"], ban["captcha_message_id"]
                    )
                except:
                    logger.exception(
                        f"Can't delete message user_id={ban['user_id']}, message_id={ban['captcha_message_id']}, chat_id={ban['chat_id']}"
                    )


def captcha(update: Update, context: CallbackContext):
    """
    Создаёт капчу, и отсылает пользователю,
    при этом заносит его в базу данных, если не
    ответит на неё в течении X минут - будет кикнут
    """

    user = update.effective_user
    chat = update.effective_chat
    captcha_answer = randint(1, 8)
    kick_date = int(time.time())+CAPTCHA_REPLY_TIMEOUT
    message = update.effective_message

    if update.effective_user.username:
        username = "@" + user.username
    else:
        try:
            username = " ".join([user.first_name, user.last_name])
        except Exception:
            username = "*какая-то undefined, а не ник*"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(i, callback_data=str(i)) for i in range(1, 9)]]
    )

    captcha_msg = context.bot.send_message(
        chat_id=chat.id,
        reply_to_message_id=message.message_id,
        text="%s, выбери цифру %s" % (username, captcha_answers[captcha_answer]),
        reply_markup=keyboard,
        disable_notification=True,
    )

    # captcha_msg = update.message.reply_text(
    #     "%s, выбери цифру %s" % (username, captcha_answers[captcha_answer]), reply_markup=keyboard
    # )
    con = sqlite3.connect(DB_FILE, check_same_thread=False)
    cur = con.cursor()
    with closing(con.cursor()) as cur:
        print("INSERT INTO banlist (user_id, time, chat_id, captcha_message_id, answer) VALUES (%s, %s, %s, %s, %s)" % (user.id, kick_date, chat.id, captcha_msg.message_id, captcha_answer))
        cur.execute(
            "INSERT INTO banlist (user_id, time, chat_id, captcha_message_id, answer) VALUES (%s, %s, %s, %s, %s)" % (user.id, kick_date, chat.id, captcha_msg.message_id, captcha_answer)
        )
        con.commit()
        con.close()
    context.bot.restrictChatMember(
        chat.id, user.id, permissions=ChatPermissions(can_send_messages=False)
    )
        
#--------------------------------------------------------------------------------------------------------
def fill_act_table(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    user_id = user.id
    chat_id = chat.id
    time_mess = int(time.time())
    time_ban = int(time.time())+TIMEOUT_FOR_BAN
    con2 = sqlite3.connect(DB_FILE_A, check_same_thread=False)
    cur2 = con2.cursor()
    with closing(con2.cursor()) as cur2:
        cur2.execute("SELECT time FROM activlist WHERE time<%s" % (time_mess-TIMEOUT_FOR_BAN)
            )
        if cur2.fetchone():
            print("Такая запись в таблице есть")
            #context.bot.restrictChatMember(chat.id, user.id, permissions=ChatPermissions(can_send_messages=False))
            context.bot.ban_chat_member(chat.id, user_id)
            print("DELETE FROM activlist WHERE user_id=%s AND chat_id=%s"%(chat.id, user.id))
            cur2.execute("DELETE FROM activlist WHERE user_id=%s AND chat_id=%s" % (user.id, chat.id)
            )            
        else:
            print("Такой записи в таблице нет, записываю")
            print("INSERT INTO activlist (time, chat_id, user_id) VALUES (%s, %s, %s)" % (time_mess, chat.id, user.id))
            cur2.execute("INSERT INTO activlist (time, chat_id, user_id) VALUES (%s, %s, %s)" % (time_mess, chat.id, user.id)
            )
    con2.commit()
    
    con2.close()   
#-------------------------------------------------------------------------------------------------------

def checkCorrectlyCaptcha(update, context):
    """
    Проверяю правильность ответа пользователя на капчу,
    если ответ правильный, то ограничение readonly снимается,
    если нет, то кик через 3-ок суток и отправляется сообщение
    с направлением к админу за разблокировкой
    """

    chat = update.effective_chat
    user = update.effective_user
    message_id = update.callback_query.message.message_id
    user_captcha_answer = update.callback_query.data
    con = sqlite3.connect(DB_FILE, check_same_thread=False)
    cur = con.cursor()
    with closing(con.cursor()) as cur:
        cur.execute(
            "SELECT answer FROM banlist WHERE user_id=%s AND captcha_message_id=%s AND chat_id=%s" % (user.id, message_id, chat.id)
        )
        record = cur.fetchone()

        if record:
            # Удаляю сообщение с капчей
            context.bot.delete_message(chat.id, message_id)
            # Проверяю ответ пользователя на капчу
            if user_captcha_answer == str(record[0]):
                cur.execute(
                    "DELETE FROM banlist WHERE user_id=%s AND chat_id=%s" % (user.id, chat.id),
                )
                context.bot.restrictChatMember(
                    chat.id,
                    user.id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_polls=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True,
                        can_invite_users=True,
                        can_change_info=True,
                        can_pin_messages=True
                    ),
                )
                try:
                    if update.effective_user.username:
                        username = "@" + user.username
                    else:
                        username = " ".join([user.first_name, user.last_name])
                except Exception:
                    username = "*какой-то undefined, а не ник*"

                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Добро пожаловать в чат, %s, пожалуйста, при входе напишите кратко (а лучше нет) вашу историю с хештегом (без скобочек): (#)intro, и хештегами локации и специалиазации например: (#)intro всем привет я Василий, родом из бабруйска, продался в галеру и догреб до города мечты. (#)Madrid, (#)DevOps, (#)python и немного (#)C++ для души."
                    % username,
                )
            else:
                if update.effective_user.username:
                    username = "@" + user.username
                else:
                    try:
                        username = " ".join([user.first_name, user.last_name])
                    except Exception:
                        username = "*какая-то undefined, а не ник*"
                cur.execute(
                    "UPDATE banlist SET time=%s WHERE user_id=%s AND chat_id=%s" % (int(time.time()) + 3*24*60*60, user.id, chat.id)
                )
            con.commit()
            con.close()
#----------------------------------------------
#Отправляет в бан пользователя
def bano(update, context):
    chat = update.effective_chat
    command_user = update.effective_user
    message = update.effective_message
    member_status = message.bot.getChatMember(chat.id, command_user.id)["status"]
# Будет выполнено только если комманду прислал пользователь с административными правами
    if member_status in ["owner", "administrator", "creator"]:
        # Ищем Id пользователя для разбана, либо в
        # пересланном сообщении либо указанное аргументом в команде
        command = message["text"].split(" ")
        if len(command) > 1:
            user_id = command[1]
        elif "reply_to_message" in message.to_dict():
            user_id = message.reply_to_message.to_dict()["from"]["id"]
        else:
            return
# Баним пользователя  и отбираем у него права
#       context.bot.ban_chat_member(chat.id, user_id)
        context.bot.restrictChatMember(chat.id,user_id,permissions=ChatPermissions(can_send_messages=False))
#----------------------------------------------

def unban(update, context):
    """ Убирает из бани пользователя """
    chat = update.effective_chat
    command_user = update.effective_user
    message = update.effective_message
    member_status = message.bot.getChatMember(chat.id, command_user.id)["status"]

    # Будет выполнено только если комманду прислал администратор
    if member_status in ["owner", "administrator", "creator"]:
        # Ищем Id пользователя для разбана, либо в
        # пересланном сообщении либо указанное аргументом в команде
        command = message["text"].split(" ")
        if len(command) > 1:
            user_id = command[1]
        elif "reply_to_message" in message.to_dict():
            user_id = message.reply_to_message.to_dict()["from"]["id"]
        else:
            return

        # Снимаем бан и возвращаем права
        context.bot.unban_chat_member(chat.id, user_id, only_if_banned=True)
        context.bot.restrictChatMember(
            chat.id,
            user_id,
            permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_polls=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True,
                        can_invite_users=True,
                        can_change_info=True,
                        can_pin_messages=True
            ),
        )

        # Убираем из бд оставшиеся записи бана
        con = sqlite3.connect(DB_FILE, check_same_thread=False)
        cur = con.cursor()       
        with closing(con.cursor()) as cur:
            cur.execute(
                "SELECT captcha_message_id FROM banlist WHERE user_id=%s AND chat_id=%s" % (user_id, chat.id)
            )
            captcha_message_id = cur.fetchone()

            if captcha_message_id:
                try:
                    context.bot.delete_message(chat.id, captcha_message_id[0])
                except BadRequest:
                    pass

            cur.execute(
                "DELETE FROM banlist WHERE user_id=%s AND chat_id=%s" % (user_id, chat.id)
            )
            con.commit()
            con.close()

def main():
    global dispatcher
    """
    Запускаем бота, создаём вебхуки,
    привязываем обработчики и фильтры.
    """

    updater = Updater(token=os.getenv("TG_BOT_TOKEN", ""))
    dispatcher = updater.dispatcher
    filter = FilterNewChatMembers()
    dispatcher.add_handler(MessageHandler(filter, captcha))
    filter = FilterMessageMembers()
    dispatcher.add_handler(MessageHandler(filter,fill_act_table))


    dispatcher.add_handler(CallbackQueryHandler(checkCorrectlyCaptcha))
    dispatcher.add_handler(CommandHandler("unban", unban))
    dispatcher.add_handler(CommandHandler("ban", bano))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    # Connect to DB
    if not os.path.isfile(DB_FILE):
        con = sqlite3.connect(DB_FILE, check_same_thread=False)
        cur = con.cursor()
        cur.execute(
          """
            CREATE TABLE banlist
            (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            user_id INT NOT NULL,
            time timestamp NOT NULL,
            chat_id BIGINT NOT NULL,
            captcha_message_id INT NOT NULL,
            answer INT NOT NULL);
        """
        )
        con.commit()
        
        con.close()

#---------------------------------------------------------------
    if not os.path.isfile(DB_FILE_A):
        con2 = sqlite3.connect(DB_FILE_A, check_same_thread=False)
        cur2 = con2.cursor()
        cur2.execute(
          """
            CREATE TABLE activlist
            (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            time timestamp NOT NULL,
            chat_id BIGINT NOT NULL,
            user_id INT NOT NULL);
        """
        )
        con2.commit()
        
        con2.close()       
        
#---------------------------------------------------------------
    # Словарь для конвертация цифр на слова
captcha_answers = {
        1: "OДИH",
        2: "ДВA",
        3: "TPИ",
        4: "ЧETЫPE",
        5: "ПЯTЬ",
        6: "ШECTЬ",
        7: "CEMЬ",
        8: "ВOCEMЬ",
    }

logger.info("Starting ban thread")
    # Второстепенный поток бана пользователей
threading.Thread(target=banUser).start()

    # Тело бота
logger.info("Starting main bot process")
main()
