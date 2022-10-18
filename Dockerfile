FROM python:3.10

ENV PYTHONUNBUFFERED True

ENV APP_HOME /app
ENV RUN_LOCAL=False
ENV PORT=8080
ENV HOST=0.0.0.0

WORKDIR $APP_HOME
COPY . ./
COPY ./app ./

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD exec gunicorn --bind :$PORT --worker-class uvicorn.workers.UvicornWorker --threads 4 --timeout 0 app:app
