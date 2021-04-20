# libs
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler, MessageFilter
from telegram import Bot, ReplyKeyboardMarkup, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.utils.request import Request

import config
import db

# creating bot

bot = Bot(config.data.token)
upd = Updater(bot=bot, use_context=True)
dp = upd.dispatcher

# filters

OperatorsChat = Filters.chat(config.data.operators_chat)
AdminChat = Filters.chat(config.data.admin_chat)
PrivateChat = Filters.chat_type.private

# logging
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

import time
import datetime


def hello(update, context):
    update.message.reply_text("""
Расскажи максимально подробно о ситуации, которая произошла с тобой или твоим знакомым. 

Напиши нам:
1) Свои ФИО, возраст и контактный телефон. 
2) Свой университет и твой статус в нем. 
3) То, что происходит прямо сейчас. Если повязали, расскажи обо всех деталях и о том, применялось ли насилие. Если вдруг есть фото/видео задержания, пришли его нам.
4) Если ситуация находится на стадии судебного разбирательства, подробно расскажи об этом. 
5) Если есть ещё что-то, что мы должны знать, — рассказывай. 

И ещё: все обязательно будет хорошо!
""")

dp.add_handler(CommandHandler('start', hello))

## ask operator scenario

# utils
def mention(op):
    return f"@{op['username']}" if op['username'] else f"<a href='tg://user?id={op['id']}'>{op['name']}</a>"

def mention_operators(flags):
    operators = db.get_subscribers(flags)
    return " ".join(map(mention, operators))

def uid_flag(uid):
    return f'id{uid}'

def userflag(user):
    return {'flag': uid_flag(user.id),
            'comment': '@'+user.username if user.username else f'{user.first_name} {user.last_name}'}

# callback

def forward_to_operators(update, context):
    # here should be powerful flag machine
    flags = ['all']
    new_user = not db.any_questions(update.effective_user)
    if new_user:
        flags.append('new')
        db.add_flag(**userflag(update.effective_user))
    flags.append(userflag(update.effective_user)['flag'])
    # then just forward and mention
    mention = mention_operators(flags)
    header = bot.send_message(chat_id=config.data.operators_chat,
                              text=f"<code>[открыт]</code>\n{mention}",
                              parse_mode=ParseMode.HTML)
    forward = update.message.forward(config.data.operators_chat)
    # and add question to database
    db.add_question(update.effective_user, update.message, forward, header)
    
    # instant reply
    update.message.reply_text("Мы получили твоё сообщение и скоро обязательно ответим!")

dp.add_handler(MessageHandler(PrivateChat, forward_to_operators))

## reply to user scenario

# filter replies to forwarded messages
class _ReplyToBotForwardedFilter(MessageFilter):
    def filter(self, message):
        try:
            reply = message.reply_to_message
            return (reply.from_user.id == bot.id) and bool(reply.forward_date)
        except AttributeError:
            return False

ReplyToBotForwardedFilter =  _ReplyToBotForwardedFilter()
        
def reply_to_user(update, context):
    forwarded = update.message.reply_to_message
    original = db.original_question(forwarded)
    sender_id = original['from_user']['id']
    db.subscribe(update.effective_user, uid_flag(sender_id))
    answer = bot.send_message(chat_id=sender_id,
                     text=update.message.text)
    first_answer = not db.any_answers(forwarded)
    if first_answer:
        bot.edit_message_text(chat_id=update.effective_chat.id,
                          message_id=original['header_id'],
                          text="<code>[закрыт]</code>",
                          parse_mode=ParseMode.HTML)
    db.add_answer(forwarded, answer)
    

dp.add_handler(MessageHandler(ReplyToBotForwardedFilter & OperatorsChat, reply_to_user))

## admin tools

# info

import json

def pretty_single(d):
    if d is None: return str(None)
    outd = d.copy()
    if '_id' in outd.keys(): outd.pop('_id')
    return json.dumps(outd, indent=2, sort_keys=True, ensure_ascii=False)

def pretty(seq):
    return "\n\n".join(map(pretty_single, seq))

# commands

def send_subscriptions(update):
    flags = db.get_flags(update.effective_user)
    print(flags)
    flag_repr = lambda f: f"<code>{f['flag']}</code>"
    flags_text = [flag_repr(f) + (f" ({f['comment']})" if f.get('comment') else "") for f in flags]
    update.message.reply_text("<b>Текущие подписки:</b>\n" + "\n".join(flags_text), parse_mode=ParseMode.HTML)

def subscribe(update, context):
    flags = update.message.text.split()[1:]
    for flag in flags:
        db.subscribe(update.effective_user, flag)
    send_subscriptions(update)

def unsubscribe(update, context):
    flags = update.message.text.split()[1:]
    for flag in flags:
        db.unsubscribe(update.effective_user, flag)
    send_subscriptions(update)

def check_subscriptions(update, context):
    return send_subscriptions(update)

dp.add_handler(CommandHandler('subscribe', subscribe, filters=OperatorsChat))
dp.add_handler(CommandHandler('unsubscribe', unsubscribe, filters=OperatorsChat))
dp.add_handler(CommandHandler('subscriptions', check_subscriptions, filters=OperatorsChat))

# utils

def say_chat_id(update, context):
    update.message.reply_text(update.message.chat_id)

dp.add_handler(CommandHandler('chatid', say_chat_id))

# error logging

def report_error(update, context):
    bot.send_message(chat_id=config.data.admin_chat,
        text=f"Error: `{context.error}`\n" +
             f"Update: ```\n{update}\n```",
        parse_mode=ParseMode.MARKDOWN_V2)

def handle_error(update, context):
    if update.effective_message:
        update.effective_message.reply_text("При обработке этого запроса в боте произошла ошибка. "+
        "Разработчики уже уведомлены!")
    report_error(update, context)

dp.add_error_handler(handle_error)


## boot

def main():
    upd.start_polling()
    upd.idle()

if __name__ == '__main__':
    main()