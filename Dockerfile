FROM python:3.8-alpine

ENV PYTHONUNBUFFERED=1\
    PYTHONDONTWRITEBYTECODE=1\
    POETRY_VERSION=1.1.2\
    POETRY_VIRTUALENVS_IN_PROJECT=1\
    POETRY_NO_INTERACTION=1

ENV ROSETTA_ROOT=/rosetta

WORKDIR /rosetta

RUN apk add libpq git

RUN apk add --update --no-cache --virtual .build-deps\
    gcc libc-dev linux-headers\
    libffi-dev libressl-dev postgresql-dev\
    python3-dev musl-dev
RUN pip install poetry==${POETRY_VERSION}
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-dev --no-root --extras deployment
RUN apk del --no-cache .build-deps

RUN adduser -D user
RUN addgroup docker
RUN addgroup user docker

RUN mkdir logs
RUN chown user:user logs
RUN chmod 755 logs

RUN mkdir archives
RUN chown user:user archives
RUN chmod 777 archives

RUN mkdir -p /genki/media
RUN chown user:user /genki/media
RUN chmod 755 /genki/media
RUN ln -s /genki/media .venv/src/genki/media

COPY . .
RUN poetry build -f wheel
RUN .venv/bin/pip install dist/*.whl

USER user

CMD [".venv/bin/python", "scripts.py", "start"]