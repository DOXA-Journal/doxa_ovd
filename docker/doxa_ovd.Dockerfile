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
COPY doxa_ovd/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip -r /tmp/requirements.txt

# Switching to an unprivileged user
RUN adduser --home /home/doxa_ovd/ --disabled-password doxa_ovd
USER doxa_ovd
WORKDIR /home/doxa_ovd/bot
COPY doxa_ovd /home/doxa_ovd/bot

# Running a bot
ENV BOT_NAME="doxa_ovd"
CMD python -u main.py
