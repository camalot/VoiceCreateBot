class EmbedField():
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def to_dict(self):
        return self.__dict__
