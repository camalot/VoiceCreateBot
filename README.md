# VoiceCreateBot


[![Docker Publish](https://github.com/camalot/voice-create-bot-docker/actions/workflows/publish-main.yml/badge.svg)](https://github.com/camalot/voice-create-bot-docker/actions/workflows/publish-main.yml) ![Docker Image Version (latest semver)](https://img.shields.io/docker/v/camalot/voice-create-bot-docker) ![](https://img.shields.io/docker/pulls/camalot/voice-create-bot-docker) [![join the discord](https://badgen.net/badge/icon/Join%20Discord?icon=discord&label)](http://discord.darthminos.tv/)

<!-- ![](https://dcbadge.vercel.app/api/shield/262031734260891648)  -->
<!-- ![](https://dcbadge.vercel.app/api/shield/bot/571011576618811402) -->

A dedicated bot for creating dynamic voice channels. Keep your voice channel count down. Allowing users to create their own channels without having to give them permissions to do so.

- Supports multiple **Create Channels**. Allowing different permissions to each **Create Channel**.
- Supports changing voice bitrate
- Dynamic channel names. Uses a custom api to dynamically generate a channel name
- Support for **Stage Channels** in *Community Discords*
- Supports per-server language (looking for more translations)

For help with the code, or the bot [join the discord](http://discord.darthminos.tv)
# INSTALL


## ENVIRONMENT VARIABLES

| NAME | DESCRIPTION | REQUIRED | DEFAULT |  
|---|---|---|---|  
| VCB_DB_PATH | The path to the SQLITE database file | `false` | `./voice.db` |  
| VCB_MONGODB_URL | MongoDB connection string | `false` | `null` |  
| DISCORD_BOT_TOKEN | The discord bot token | `true` | `null` |  
| VCB_DISCORD_CLIENT_ID | The app client id | `true` | `null` |  
| BOT_OWNER | The discord ID of the bot owner | `true` | `null` |  
| LOG_LEVEL | The minimum log level. `[DEBUG\|INFO\|WARNING\|ERROR\|FATAL]` | `false` | `DEBUG` |  
| DB_PROVIDER | The database provider to use `[MONGODB\|SQLITE]` | `false` | `MONGODB` |  
| LANGUAGE | The default language of the bot to fall back to | `false` | `en-us` |

## DATABASE SUPPORT

MongoDB is the preferred database provider. SQLITE might not be fully compatible.

If using SQLITE provider, you will want to mount the /data volume, so the database file is persisted 

## HOW TO RUN THE BOT LOCALLY

- clone the repo
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

```shell
docker run --rm \
--restart=unless-stopped \
-e VCB_DISCORD_CLIENT_ID="<FILL IN YOUR DISCORD CLIENT ID>" \
-e DISCORD_BOT_TOKEN="<FILL IN YOUR DISCORD BOT TOKEN>" \
-e BOT_OWNER="<FILL IN YOUR DISCORD USER ID>" \
-e VCB_MONGODB_URL="mongodb://mdbroot:toorbdm@mongodb:27017/admin" \
-e LOG_LEVEL="INFO" \
-e DB_PROVIDER="MONGODB" \
camalot/voice-create-bot-docker:latest

```

## INVITE TO DISCORD

`https://discordapp.com/oauth2/authorize?client_id=<CLIENT_ID>&permissions=8&scope=bot`

## CONTRIBUTORS

_Note:
This started out as a fork of the bot by [@SamSanai](https://github.com/SamSanai). It has sense been completely rewritten and is no longer anything that it once was._