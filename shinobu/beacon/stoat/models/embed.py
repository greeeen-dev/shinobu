import stoat

class EmbedField:
    def __init__(self, name, value):
        self.name = name
        self.value = value

class Embed(stoat.SendableEmbed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields = []
        self.raw_description = kwargs.get('description', None)
        self.raw_colour = kwargs.get('color', None) or kwargs.get('colour', None)

    @property
    def description(self):
        if self.fields:
            return (
                (self.raw_description + '\n\n') if self.raw_description else ''
            )+ '\n\n'.join([f'**{field.name}**\n{field.value}' for field in self.fields])
        else:
            return self.raw_description

    @description.setter
    def description(self, value):
        self.raw_description = value

    @property
    def colour(self):
        if type(self.raw_colour) is int:
            return '#' + hex(self.raw_colour)[2:].zfill(6)

        return self.raw_colour

    @colour.setter
    def colour(self, value):
        self.raw_colour = value

    def add_field(self, name, value):
        self.fields.append(EmbedField(name, value))

    def clear_fields(self):
        self.fields = []

    def insert_field_at(self, index, name, value):
        self.fields.insert(index, EmbedField(name, value))

    def remove_field(self, index):
        self.fields.pop(index)

    def set_field_at(self, index, name, value):
        self.fields[index] = EmbedField(name, value)