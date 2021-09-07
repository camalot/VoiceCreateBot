BEGIN TRANSACTION;
CREATE TABLE `TEMP_GS` (`guildID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER, `defaultRole` TEXT DEFAULT '@everyone');
INSERT INTO `TEMP_GS` SELECT guildID, channelName, channelLimit, '@everyone' FROM guildSettings;
DROP TABLE `guildSettings`;
ALTER TABLE `TEMP_GS` RENAME TO `guildSettings`;
COMMIT;
