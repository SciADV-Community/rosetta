FROM python:3.9-alpine

ENV PYTHONUNBUFFERED=1\
    PYTHONDONTWRITEBYTECODE=1\
    POETRY_VERSION=1.1.14\
    POETRY_VIRTUALENVS_IN_PROJECT=1\
    POETRY_NO_INTERACTION=1

ARG docker_gid=998

ENV ROSETTA_ROOT=/rosetta

WORKDIR /rosetta

RUN apk add libpq git gcc

RUN apk add --update --no-cache --virtual .build-deps\
    g++ libc-dev linux-headers\
    libffi-dev libressl-dev postgresql-dev\
    python3-dev musl-dev rust cargo
RUN pip install poetry==${POETRY_VERSION}
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-dev --no-root --extras deployment
RUN apk del --no-cache .build-deps

# Sometimes the docker GID is in use by the container, if so then just send it to Va11ha11a
RUN grep -q ":$docker_gid:" /etc/group && sed -i "s/$docker_gid/1111/" /etc/group

RUN adduser -D user
RUN addgroup -g ${docker_gid} docker
RUN addgroup user docker

RUN touch /var/run/docker.sock
RUN chown root:docker /var/run/docker.sock

RUN mkdir -p /rosetta/logs
RUN chown user:user /rosetta/logs
RUN chmod 755 logs

RUN mkdir -p /rosetta/archives
RUN chown user:user /rosetta/archives
RUN chmod 755 archives

RUN mkdir -p /genki/media
RUN chown user:user /genki/media
RUN chmod 755 /genki/media
RUN ln -s /genki/media .venv/lib/python3.9/site-packages/media

COPY . .
RUN poetry build -f wheel
RUN .venv/bin/pip install dist/*.whl

USER user

CMD [".venv/bin/python", "scripts.py", "start"]