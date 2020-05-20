# Rosetta

Discord bot for managing channels in playthrough servers.

## Development setup

1. Install [poetry](https://python-poetry.org/).
2. Run `poetry install`.
3. Run `poetry run config` to create a `.env` file containing important environment variables for the configuration of the bot.

## Running the bot

### Manually

Run `export $(cat .env | xargs) && poetry run start`

### Docker



## Running tests
Run `poetry run test`
