# VoiceCreateBot

Dedicated bot for creating temp voice channels with commands for changing permissions.

This bot runs on [discord.py](https://discord.gg/r3sSKJJ) rw If you need help with the code use the [discord.py server](https://discord.gg/r3sSKJJ)

As there is a very high demand for me to release the source code for my bot I've finally decided to release it.

This was just a small project that got quite big, I wrote the bot in a day so the code is pretty sloppy and sadly I couldn't give a fuck and in no way shape of form I'm saying I'm a good programmer.

Enjoy the code, don't try to release it as your own bot. :)

If you'd like to support the bot you could pay for my coffee and the servers using the link below <3  [https://www.paypal.me/ssanaizadeh](https://www.paypal.me/ssanaizadeh)


# How to setup the bot:

1. Download python using the following link:
	- https://www.python.org/downloads/release/python-373/
1. Open command prompt and paste the following:
	```shell
	pip3 install discord.py
	pip3 install validators
	```  

1. Download the bot from github
	- clone the repo using `git clone` or download the repo zip file.
1. Set environment variable `DISCORD_BOT_TOKEN` to contain your Discord Bot Token.
	- Go to the [Discord Developer site](https://discordapp.com/developers/applications/me) and create an application. You will need the Bot Token, and the application Client Id.
1. Set environment variable `ADMIN_USERS` to be a list of space separated discord user ids.
	- To get a user's id, in a text channel type `\@UserName#1111`. This is just like if you were going to mention a user, but then add a `\` in front. 
	- This will return something like `<@1234567890>`. The `1234567890` is the id.
1. Run:
	```shell
	python voicecreate.py
	```

1. Invite Bot to your discord using the following url:  
`https://discordapp.com/oauth2/authorize?client_id=<CLIENT_ID>&permissions=285213712&scope=bot`

# Run the bot in Docker

```shell
docker run \
	--rm -d \
	--restart=unless-stopped \
	-e DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN} \
	-e VCB_DB_PATH=/data \
	-v /path/to/persistent/data:/data \
	--name voice_create \
	camalot/voice-create-bot-docker:latest
```