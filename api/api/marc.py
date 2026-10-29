import pymarc
from dataclasses import dataclass
import re
import string
from collections.abc import Callable
from api.entities import SearchField, FieldElement, PairedField

# used with rstrip_chars. When we want to trim the end of a string, these are
# the ones that usually should be removed.
TRIM_CHARS = "/.,: "


def bidi(string):
    """Make string bidirectional

    Surrounds the string with First Strong Isolate \\u2068 and Pop Directional Isolate \\u2069
    More info https://en.wikipedia.org/wiki/Unicode_bidirectional_algorithm

    Args:
        string str: string to be surrounded with bidirectional characters
    """
    stripped_string = string.strip()
    if stripped_string:
        return f"\u2068{stripped_string}\u2069"
    else:
        return stripped_string


class Linkage:
    def __init__(self, field: pymarc.Field):
        if field.get("6"):
            self.parts = re.split("[-/]", field["6"])
        else:
            self.parts = [None, None]

    @property
    def tag(self):
        return self.parts[0]

    @property
    def occurence_number(self):
        return self.parts[1]

    def __str__(self):
        return f"{self.tag}-{self.occurence_number}"


@dataclass(frozen=True)
class FieldRuleset:
    tags: list
    text_sfs: str = string.ascii_lowercase
    search: list | None = None
    browse_sfs: str | None = None
    filter: Callable[..., bool] = lambda field: True
    rstrip_chars: str = ""

    def has_any_subfields(self, field: pymarc.Field) -> bool:
        return bool(self._get_subfields(field, self.text_sfs))

    def value_for(self, field: pymarc.Field):
        result = {
            "text": self._get_subfields(field, self.text_sfs)
            .rstrip(self.rstrip_chars)
            .strip(),
            "tag": field.tag,
        }

        if self.search:
            result["search"] = []
            for s in self.search:
                value = self._get_subfields(field, s["subfields"])
                if value:
                    result["search"].append(
                        SearchField(
                            field=s["field"],
                            value=self._get_subfields(field, s["subfields"]),
                        )
                    )

        if self.browse_sfs:
            result["browse"] = self._get_subfields(field, self.browse_sfs)

        return FieldElement(**result)

    def _get_subfields(self, field: pymarc.Field, subfields: str):
        result = " ".join(field.get_subfields(*tuple(subfields)))
        if field.tag == "880":
            result = bidi(result)
        return result


class Processor:
    def __init__(self, record: pymarc.record.Record):
        self.record = record

    def generate_unpaired_fields(self, rulesets: tuple) -> list:
        result = []
        for ruleset in rulesets:
            for field in self.record.get_fields(*ruleset.tags):
                if ruleset.filter(field) and ruleset.has_any_subfields(field):
                    value = ruleset.value_for(field)
                    if value not in result:
                        result.append(value)
        return result

    def generate_paired_fields(self, rulesets: tuple) -> list:
        result = []
        for ruleset in rulesets:
            for fields in self._get_paired_fields_for(ruleset):
                if ruleset.filter(fields["original"]):
                    r = {}
                    for key in fields:
                        r[key] = ruleset.value_for(fields[key])
                    result.append(PairedField(**r))
        return result

    def _get_original_for_tags(self, tags: tuple) -> list:
        def linkage_has_tag(field):
            return Linkage(field).tag in tags

        return list(filter(linkage_has_tag, self.record.get_fields("880")))

    def _get_paired_fields_for(self, ruleset: FieldRuleset) -> list:
        mapping = {}
        for field in self._get_original_for_tags(ruleset.tags):
            mapping[str(Linkage(field))] = field

        results = []
        for field in self.record.get_fields(*ruleset.tags):
            if ruleset.has_any_subfields(field):
                original = mapping.pop(
                    f"{field.tag}-{Linkage(field).occurence_number}", None
                )
                if original:
                    results.append({"transliterated": field, "original": original})
                else:
                    results.append({"original": field})

        return results + [
            {"original": f} for f in mapping.values() if ruleset.has_any_subfields(f)
        ]
