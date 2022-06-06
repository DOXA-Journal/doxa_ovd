FROM python:3.9-alpine

# Metadata
LABEL MAINTAINERS="chimera (chimera@chimera.website)"

# Installing apps
RUN apk add build-base libffi-dev

# Creating virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
# Some magic: next line also activates venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip -r /tmp/requirements.txt

# Switching to an unprivileged user
RUN adduser --home /home/doxa_bot/ --disabled-password doxa_bot
USER doxa_bot
WORKDIR /home/doxa_bot/bot
COPY . /home/doxa_bot/bot

# Running a bot
ENV BOT_NAME="doxa_bot"
CMD python -u main.py
