FROM python:3.13

ENV PYTHONUNBUFFERED True

ENV APP_HOME /app
ENV RUN_LOCAL=False
ENV PORT=8080
ENV HOST=0.0.0.0
ENV POETRY_VERSION=1.2.2

RUN pip install "poetry==$POETRY_VERSION"

WORKDIR $APP_HOME
COPY . ./
COPY vrf_worker ./

RUN poetry config virtualenvs.create false \
&& poetry install --no-dev --no-interaction --no-ansi

CMD exec gunicorn --bind :$PORT --worker-class uvicorn.workers.UvicornWorker --threads 4 --timeout 0 app:app
