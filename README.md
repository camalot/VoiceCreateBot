# VoiceCreateBot


[![Docker Publish](https://github.com/camalot/voice-create-bot-docker/actions/workflows/publish-main.yml/badge.svg)](https://github.com/camalot/voice-create-bot-docker/actions/workflows/publish-main.yml) ![Docker Image Version (latest semver)](https://img.shields.io/docker/v/camalot/voice-create-bot-docker) ![Docker Pulls](https://img.shields.io/docker/pulls/camalot/voice-create-bot-docker)

A dedicated bot for creating dynamic voice channels. Keep your voice channel count down. Allowing users to create their own channels without having to give them permissions to do so.

## FEATURES

| | | |
|---|---|---|
| Multiple Create Channels | :heavy_check_mark: | |
| Different Permissions Per Create Channel | :heavy_check_mark: | |
| Random Channel Names | :heavy_check_mark: | |
| Ability for user to change channel name | :heavy_check_mark: | |
| Stage Channels | :heavy_check_mark: | |
| Per-Server Language | :heavy_check_mark: | |
| Change command prefix per-server | :heavy_check_mark: | |
| Admin role to control bot | :heavy_check_mark: | |
| Admin commands | :heavy_check_mark: | |
| Set channel limits | :heavy_check_mark: | |
| Set channel bitrate | :heavy_check_mark: | |
| User specific settings | :heavy_check_mark: | |
| Set channel name from game | :heavy_check_mark: | |

For help with the code, or the bot [join the discord](http://discord.darthminos.tv)
## INSTALL

### ENVIRONMENT VARIABLES

| NAME | DESCRIPTION | REQUIRED | DEFAULT |
|---|---|---|---|
| VCB_MONGODB_URL | MongoDB connection string | `false` | `null` |
| VCB_MONGODB_DBNAME | MongoDB database name | `true` | `voicecreate_v2` |
| VCB_DISCORD_BOT_TOKEN | The discord bot token | `true` | `null` |
| VCB_DISCORD_CLIENT_ID | The app client ID | `true` | `null` |
| VCB_BOT_OWNER | The discord ID of the bot owner | `true` | `null` |
| VCB_LOG_LEVEL | The minimum log level. `[DEBUG\|INFO\|WARNING\|ERROR\|FATAL]` | `false` | `DEBUG` |
| VCB_LANGUAGE | The default language of the bot to fall back to | `false` | `en-us` |
| | | | |
| VCBE_CONFIG_METRICS_ENABLED | Enable the prometheus exporter | `false` | `false` |
| VCBE_CONFIG_METRICS_PORT | Running port for the prometheus exporter | `false` | `8932` |
| VCBE_CONFIG_METRICS_POLLING_INTERVAL | How often, in seconds, to poll the metrics | `false` | `60` |

## DATABASE SUPPORT

## HOW TO RUN THE BOT LOCALLY

- clone the repository
- Create a `.env` file in the root directory with the above environment variables
- run `pip install -r ./setup/requirements.txt`
- run `python ./main.py`
- invite the bot to your discord (see below)

## HOW TO RUN THE BOT VIA DOCKER

### DOCKER COMPOSE

- Clone [camalot/voice-create-bot-docker](https://github.com/camalot/voice-create-bot-docker)
- Modify the docker-compose.yml
- run `docker-compose up`

### DOCKER

``` shell
docker run --rm \
--restart=unless-stopped \
-e VCB_DISCORD_CLIENT_ID="<FILL IN YOUR DISCORD CLIENT ID>" \
-e DISCORD_BOT_TOKEN="<FILL IN YOUR DISCORD BOT TOKEN>" \
-e BOT_OWNER="<FILL IN YOUR DISCORD USER ID>" \
-e VCB_MONGODB_URL="mongodb://mdbroot:toorbdm@mongodb:27017/admin" \
-e LANGUAGE="en-us" \
-e LOG_LEVEL="INFO" \
ghcr.io/camalot/voicecreatebot:latest

```

## INVITE TO DISCORD

`https://discordapp.com/oauth2/authorize?client_id=<CLIENT_ID>&permissions=8&scope=bot`