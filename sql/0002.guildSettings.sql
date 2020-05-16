BEGIN TRANSACTION;
CREATE TABLE `TEMP_GS` (`guildID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER);
INSERT INTO `TEMP_GS` SELECT guildID, channelName, channelLimit FROM guildSettings;
DROP TABLE `guildSettings`;
ALTER TABLE `TEMP_GS` RENAME TO `guildSettings`;
COMMIT;
