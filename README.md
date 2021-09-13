# VoiceCreateBot


[![Docker Publish](https://github.com/camalot/voice-create-bot-docker/actions/workflows/publish-main.yml/badge.svg)](https://github.com/camalot/voice-create-bot-docker/actions/workflows/publish-main.yml) ![](https://img.shields.io/docker/pulls/camalot/voice-create-bot-docker) [![join the discord](https://badgen.net/badge/icon/Join%20Discord?icon=discord&label)](http://discord.darthminos.tv/)

<!-- ![](https://dcbadge.vercel.app/api/shield/262031734260891648)  -->
<!-- ![](https://dcbadge.vercel.app/api/shield/bot/571011576618811402) -->

A dedicated bot for creating dynamic voice channels. Keep your voice channel count down. Allowing users to create their own channels without having to give them permissions to do so.

- Supports multiple **Create Channels**. Allowing different permissions to each **Create Channel**.
- Supports changing voice bitrate
- Dynamic channel names. Uses a custom api to dynamically generate a channel name
- Support for **Stage Channels** in *Community Discords*

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



## HOW TO RUN THE BOT LOCALLY

- Create a `.env` file in the root directory with the above environment variables
- run `pip install -r ./setup/requirements.txt`
- run `python ./main.py`
- invite the bot to your discord (see below)

## HOW TO RUN THE BOT VIA DOCKER



## INVITE TO DISCORD

https://discordapp.com/oauth2/authorize?client_id=<CLIENT_ID>&permissions=8&scope=bot

## CONTRIBUTORS

_Note:
This started out as a fork of the bot by [@SamSanai](https://github.com/SamSanai). It has sense been completely rewritten and is no longer anything that it once was._