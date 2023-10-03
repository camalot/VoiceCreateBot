class GuildCategoryCreateChannel:
    def __init__(self, ownerId: int, categoryId: int, channelId: int, useStage: bool):
        self.owner_id = int(ownerId)
        self.category_id = int(categoryId)
        self.channel_id = int(channelId)
        self.use_stage = useStage
