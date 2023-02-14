FROM python:3.9-alpine

ENV PYTHONUNBUFFERED=1\
    PYTHONDONTWRITEBYTECODE=1\
    POETRY_VERSION=1.3.2\
    POETRY_VIRTUALENVS_IN_PROJECT=1\
    POETRY_NO_INTERACTION=1
ARG docker_gid=998
ENV ROSETTA_ROOT=/rosetta

WORKDIR /rosetta

# Dependencies
COPY poetry.lock pyproject.toml ./
RUN apk add libpq git gcc\
    && apk add --update --no-cache --virtual .build-deps\
    g++ libc-dev linux-headers\
    libffi-dev libressl-dev postgresql-dev\
    python3-dev musl-dev rust cargo\
    && pip install poetry==${POETRY_VERSION}\
    && poetry install --no-dev --no-root --extras deployment\
    && apk del --no-cache .build-deps

# Sometimes the docker GID is in use by the container, if so then just send it to Va11ha11a
RUN grep -q ":$docker_gid:" /etc/group && sed -i "s/$docker_gid/1111/" /etc/group

# Everything else
COPY . .
RUN adduser -D user\
    && addgroup -g ${docker_gid} docker\
    && addgroup user docker\
    && touch /var/run/docker.sock\
    && chown root:docker /var/run/docker.sock\
    && mkdir -p logs archives /genki/media\
    && chown user:user -R logs archives /genki/media\
    && chmod 755 logs archives /genki/media\
    && ln -s /genki/media .venv/lib/python3.9/site-packages/media\
    && poetry build -f wheel\
    && .venv/bin/pip install dist/*.whl

USER user

CMD [".venv/bin/python", "scripts.py", "start"]
