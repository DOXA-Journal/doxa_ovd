from pymongo import MongoClient

import config

from utils import uid_flag, comment, flagrepr

from datetime import datetime, timedelta

timeformat = "%Y-%m-%d_%H:%M:%S"

def timeparse(timestring):
    return datetime.strptime(timestring, timeformat)

def timestamp():
    return datetime.now().strftime(timeformat)

mc = MongoClient()
db = mc[config.data.mongo_db]

# utils

def userinfo(user):
    return { 'name' : f"{user.first_name} {user.last_name}"
           , 'username': user.username
           , 'id': user.id }

def uid(user):
    return {'id': user.id}

# all users for broadcast

def register(user):
    db.users.update_one({'id': user.id},
                        {'$set': {'username': user.username}},
                        upsert=True)

def user_ids():
    return list(map(lambda u: u['id'], db.users.find()))

## db operations

# flags

def subscribe(user, flag, flag_repr=None):
    db.flags.update_one(
                    {'flag': flag},
                    {'$push': {'subscribers': userinfo(user)},
                     '$set': {'flag_repr': flag_repr or flag}},
                    upsert=True)


def subscribe_thread(user, thread):
    db.flags.update_one(
        {'flag': thread['flag']},
        {'$set': {'flag_repr': thread['flag_repr'],
                  'comment': thread['user_comment']},
         '$push': {'subscribers': userinfo(user)}},
        upsert=True
    )

def unsubscribe(user, flag):
    db.flags.update_many({'$or': [{'flag': flag}, {'flag_repr': flag}]},
                    {'$pull': {'subscribers': uid(user)}})

def unsubscribe_all(user):
    db.flags.update_many(dict(),
                    {'$pull': {'subscribers': uid(user)}})


def get_flags(user):
    return list(db.flags.find({'subscribers': {'$elemMatch': uid(user)}}))


def get_subscribers(flags):
    d = dict()
    for f in db.flags.find({'$or': [{'flag': {'$in': flags}}, {'flag_repr': {'$in': flags}}]}):
        for s in f['subscribers']:
            d[s['id']] = s
    return list(d.values())

# threads (questions/answers)


def add_question(user, message, forward, header):
    q = {'from_user': uid(user),
         'time': timestamp(),
         'content': message.text,
         'forward_id': [forward.message_id]}
    db.threads.update_one({'flag': uid_flag(user.id)},
                            {'$push': {'questions': q},
                             '$set':
                                { 'user_id': user.id,
                                  'flag_repr': flagrepr(user),
                                  'user_comment': comment(user),
                                  'header_id': header.message_id,
                                  'closed': False }
                            },
                            upsert=True)

def get_thread(user_id):
    return db.threads.find_one({'user_id': user_id})

def get_thread_by_forward(forward):
    return db.threads.find_one({'questions': {'$elemMatch': {'forward_id': forward.message_id}}})


def add_answer(forward, answer, to_user_id):
    a = {'text': answer.text,
         'time': timestamp(),
         'operator': answer.from_user.username,
         'id': answer.message_id}
    db.threads.update({'user_id': to_user_id},
                      {'$push': {'answers': a},
                       '$set': {'closed': True,
                                'new': False}})
