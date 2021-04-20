from pymongo import MongoClient

import config

from datetime import datetime, timedelta

timeformat = "%Y-%m-%d_%H:%M:%S"

def timeparse(timestring):
    return datetime.strptime(timestring, timeformat)

def timestamp():
    datetime.now().strftime(timeformat)

mc = MongoClient()
db = mc[config.data.mongo_db]

# utils

def userinfo(user):
    return { 'name' : f"{user.first_name} {user.last_name}"
           , 'username': user.username
           , 'id': user.id }

def uid(user):
    return {'id': user.id}

## db operations

# flags

def add_flag(flag, comment):
    db.flags.insert({'flag': flag,
                     'comment': comment,
                     'subscribers': []})

def subscribe(user, flag):
    db.flags.update_one(
                    {'flag': flag},
                    {'$push': {'subscribers': userinfo(user)}},
                    upsert=True)

def unsubscribe(user, flag):
    db.flags.update({'flag': flag},
                    {'$pull': {'subscribers': uid(user)}})


def get_flags(user):
    return list(db.flags.find({'subscribers': {'$elemMatch': uid(user)}}))


def get_subscribers(flags):
    d = dict()
    for f in db.flags.find({'flag': {'$in': flags}}):
        for s in f['subscribers']:
            d[s['id']] = s
    return list(d.values())

# questions

def register_question(text):
    return {'time': timestamp(),
            'text': text}

def any_questions(user):
    u = db.users.find_one(uid(user))
    return u and bool(u.get('questions'))

def add_question(user, message, forward, header):
    q = {'from_user': uid(user),
         'time': timestamp(),
         'content': message.text,
         'forward_id': [forward.message_id],
         'header_id': header.message_id}
    db.users.update(uid(user),
                    {'$push': {'questions': q}},
                    upsert=True)
    q.update({'answers': []})
    db.questions.insert_one(q)

def original_question(forward):
    return db.questions.find_one({'forward_id': forward.message_id})

def add_answer(forward, answer):
    db.questions.update_one({'forward_id': forward.message_id},
                            {'$push': {'answers': {'text': answer.text,
                                                   'time': timestamp(),
                                                   'operator': answer.effective_user.username}}})