# libs
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler, MessageFilter
from telegram import Bot, ReplyKeyboardMarkup, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.utils.request import Request
from telegram.error import TelegramError

from utils import mention, uid_flag, flagrepr

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
1) Свои <u>ФИО</u>, <u>возраст</u> и <u>контактный телефон</u>. 
2) Свой <u>университет</u> и твой <u>статус</u> в нем. 
3) То, что происходит прямо сейчас. Если <u>повязали</u>, расскажи обо всех деталях и о том, применялось ли насилие. Если вдруг есть <u>фото/видео</u> задержания, пришли его нам.
4) Если ситуация находится на стадии <u>судебного разбирательства</u>, подробно расскажи об этом. 
5) Если есть ещё что-то, что мы должны знать, — рассказывай. 

И ещё: <b>все обязательно будет хорошо</b>!
""",
    parse_mode=ParseMode.HTML)
    db.register(update.effective_user)

dp.add_handler(CommandHandler('start', hello))

## ask operator scenario

# callback

def mention_operators(flags):
    operators = db.get_subscribers(flags)
    return " ".join(map(mention, operators))

def forward_to_operators(update, context):
    # forward
    forward = update.message.forward(config.data.operators_chat)
    
    # check thread
    thread = db.get_thread(update.effective_user.id)

    # instant reply
    if not thread or thread.get('closed'):
        update.message.reply_text("Мы получили твоё сообщение и скоро обязательно ответим!")

    # flag machine
    flags = list()
    flags.append('открыто')
    if not thread: flags.append('впервые')
    flags.append(flagrepr(update.effective_user))

    # get subscribers
    operators = db.get_subscribers(flags)
    
    # update ui
    outdated_header = thread['header_id'] if thread else None
    if outdated_header and not thread['closed']:
        try:
            bot.delete_message(chat_id=config.data.operators_chat,
                               message_id=outdated_header)
        except:
            pass
    tags = map(lambda s: "#"+s, flags)
    tag_text = ' '.join(tags)
    mention_text = " ".join(map(mention, operators))
    header = bot.send_message(chat_id=config.data.operators_chat,
                              text=f"[ {tag_text} ]\n{mention_text}",
                              parse_mode=ParseMode.HTML)
    
    # add question
    db.add_question(update.effective_user, update.message, forward, header)

dp.add_handler(MessageHandler(PrivateChat & ~Filters.command, forward_to_operators))

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
    thread = db.get_thread_by_forward(forwarded)
    db.subscribe_thread(update.effective_user, thread)
    answer_id = update.message.copy(chat_id=thread['user_id'])
    # update ui
    if not thread['closed']:
        bot.edit_message_text(chat_id=update.effective_chat.id,
                              message_id=thread['header_id'],
                              text=f"[ #{thread.get('flag_repr')} ]")
    db.add_answer(forwarded, update.message, thread['user_id'])


dp.add_handler(MessageHandler(ReplyToBotForwardedFilter & OperatorsChat & ~Filters.command, reply_to_user))

# close comamnd 

def close_thread(update, context):
    forwarded = update.message.reply_to_message
    thread = db.get_thread_by_forward(forwarded)
    db.unsubscribe(update.effective_user, thread['flag'])
    if not thread['closed']:
        bot.edit_message_text(chat_id=update.effective_chat.id,
                              message_id=thread['header_id'],
                              text=f"[ #{thread.get('flag_repr')} ]")
        db.close_thread(thread)

dp.add_handler(CommandHandler('close', close_thread, filters=OperatorsChat))

## subscription management

def parse_flags(text):
    return map(lambda s: s.lstrip('@#'), filter(lambda s: not s.startswith("/"), text.split()))


def send_subscriptions(update):
    flags = db.get_flags(update.effective_user)
    view_flag = lambda f: f.get('flag_repr') or f.get('flag')
    view_comment = lambda f: f" ({f.get('comment')})" if f.get('comment') else ""
    flags_text = [f"#{view_flag(f)}{view_comment(f)}" for f in flags]
    update.message.reply_text("<b>Текущие подписки:</b>\n" + "\n".join(flags_text) if flags_text else "<b>Нет текущих подписок</b>", parse_mode=ParseMode.HTML)

def subscribe(update, context):
    for flag in parse_flags(update.message.text):
        db.subscribe(update.effective_user, flag)
    return send_subscriptions(update)

def unsubscribe(update, context):
    for flag in parse_flags(update.message.text):
        db.unsubscribe(update.effective_user, flag)
    return send_subscriptions(update)

def unsubscribe_all(update, context):
    db.unsubscribe_all(update.effective_user)
    return send_subscriptions(update)

def check_subscriptions(update, context):
    return send_subscriptions(update)

dp.add_handler(CommandHandler('subscribe', subscribe, filters=OperatorsChat))
dp.add_handler(CommandHandler('unsubscribe', unsubscribe, filters=OperatorsChat))
dp.add_handler(CommandHandler('unsubscribe_all', unsubscribe, filters=OperatorsChat))
dp.add_handler(CommandHandler('subscriptions', check_subscriptions, filters=OperatorsChat))

## admin tools

# setup / testing

def say_chat_id(update, context):
    update.message.reply_text(update.message.chat_id)

def test_error(update, context):
    raise TelegramError('Test Error')

def dev_features():
    dp.add_handler(CommandHandler('chatid', say_chat_id))
    dp.add_handler(CommandHandler('test_error', test_error))

# utils

import json

def pretty_single(d):
    if d is None: return str(None)
    outd = d.copy()
    if '_id' in outd.keys(): outd.pop('_id')
    return json.dumps(outd, indent=2, sort_keys=True, ensure_ascii=False)

def pretty(seq):
    return "\n\n".join(map(pretty_single, seq))

# info

def thread_info(update, context):
    flag = update.effective_message.text.split()[1]
    thread = db.get_thread_by_userflag(flag)
    update.message.reply_text(f"<code>{pretty_single(thread)}</code>",
                              parse_mode=ParseMode.HTML)

dp.add_handler(CommandHandler('thread', thread_info, filters=AdminChat))
    

# broadcast

def broadcast(text):
    for user_id in db.user_ids():
        try:
            bot.send_message(chat_id=user_id,
                             text=text)
        except:
            time.sleep(1)
            try:
                bot.send_message(chat_id=user_id,
                                 text=text)
            except:
                pass


BROADCAST_INPUT = 'binput'

def broadcast_start(update, context):
    update.message.reply_text("Введите текст для распространения:")
    return BROADCAST_INPUT

def broadcast_share_input(update, context):
    broadcast(update.message.text)
    return ConversationHandler.END

dp.add_handler(ConversationHandler(
    entry_points=[CommandHandler('broadcast', broadcast_start, filters=AdminChat)],

    states={
       BROADCAST_INPUT: [MessageHandler(Filters.text & ~Filters.command, broadcast_share_input)]
    },

    fallbacks = [CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
))


# error logging

def report_error(update, context):
    bot.send_message(chat_id=config.data.admin_chat,
        text=f"<code>{type(context.error).__name__}</code> : {context.error}\n\n" +
             f"<code>\n{pretty_single(update.to_dict() if update else None)}\n</code>",
        parse_mode=ParseMode.HTML)

def handle_error(update, context):
    if update and update.effective_message:
        update.effective_message.reply_text("При обработке этого запроса в боте произошла ошибка. "+
        "Разработчики уже уведомлены!")
    report_error(update, context)

dp.add_error_handler(handle_error)


## boot

def main():
    upd.start_polling()
    upd.idle()

if __name__ == '__main__':
    if config.data.dev: dev_features()
    main()
