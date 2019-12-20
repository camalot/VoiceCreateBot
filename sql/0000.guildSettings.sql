CREATE TABLE
IF NOT EXISTS `guildSettings`
( `guildID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER, `prefix` TEXT DEFAULT '.' )
