def mention(op):
    return f"@{op['username']}" if op['username'] else f"<a href='tg://user?id={op['id']}'>{op['name']}</a>"

def uid_flag(uid):
    return f'id{uid}'

def comment(user):
    return '@'+user.username if user.username else f'{user.first_name} {user.last_name}'