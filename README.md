# rosetta 

![Build Status](https://github.com/SciADV-Community/rosetta/workflows/CI%20%26%20CD/badge.svg)

Discord bot for managing channels in playthrough servers.

## Development setup

1. Install [poetry](https://python-poetry.org/).
2. Run `poetry install`.
3. Run `poetry run config` to create a `.env` file containing important environment variables for the configuration of the bot.

## Running the bot

### Manually

Run `export $(cat .env | xargs) && poetry run start`

### Docker

1. Have `Docker` and `docker-compose` installed.
2. Run `docker-compose build`.
3. Configure the bot with `poetry run config`.
4. Run `docker-compose up`.

#### Please note

You might need to specify the `docker_gid` arg to the group id of the `docker` group on the **host** environment such that the container can use the passed in `docker.sock` socket to run the chat exporter. You may specify it in the `docker-compose.yml` file like so:

```yml
...
build:
    context: .
    args:
        docker_gid: 1001
...
```

## Running tests

Run `poetry run test`
