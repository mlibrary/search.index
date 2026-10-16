from api.entities import TextField, PairedField


class SolrDocProcessor:
    kinds = {
        "plain": "get",
        "paired_field": "get_paired_field",
        "text_field": "get_text_field",
        "list": "get_list",
        "academic_discipline": "get_academic_discipline",
    }

    def __init__(self, data: dict):
        self.data = data

    def get(self, key):
        return self.data.get(key)

    def get_paired_field(self, key):
        values = self.data.get(key) or []
        match len(values):
            case 0:
                return []
            case 1:
                return [PairedField(original=TextField(text=values[0]))]
            case _:
                return [
                    PairedField(
                        transliterated=TextField(text=values[0]),
                        original=TextField(text=values[1]),
                    )
                ]

    def get_text_field(self, key):
        field_values = self.data.get(key)
        if type(field_values) is str:
            field_values = [field_values]
        elif field_values is None:
            field_values = []
        return [TextField(text=value) for value in field_values]

    def get_list(self, key):
        data = self.data.get(key, [])
        if isinstance(data, str):
            return [data]
        return data

    def get_academic_discipline(self, key):
        return [{"list": discipline.split(" | ")} for discipline in self.get_list(key)]

    def get_kind(self, field, kind="plain"):
        return getattr(self, self.kinds[kind])(field)
