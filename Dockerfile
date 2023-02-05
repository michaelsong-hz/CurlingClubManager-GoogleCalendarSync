FROM python:3.11-alpine

COPY crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab

RUN pip install pipenv
ENV PROJECT_DIR /app
WORKDIR ${PROJECT_DIR}
COPY Pipfile Pipfile.lock ${PROJECT_DIR}/
RUN pipenv install --system --deploy

COPY main.py /app/main.py
COPY config.json /app/config.json

CMD ["crond", "-f"]
