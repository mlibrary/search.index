class BaseCSL:
    # these come from here: https://docs.citationstyles.org/en/stable/specification.html#appendix-iii-types
    # yes, there is a mix of snake case and kebab case
    TYPE_ORDER = [
        "article-journal",
        "article-magazine",
        "article-newspaper",
        "bill",
        "broadcast",
        "chapter",
        "dataset",
        "entry-dictionary",
        "entry-encyclopedia",
        "figure",
        "interview",
        "legal_case",
        "legislation",
        "map",
        "motion_picture",
        "musical_score",
        "pamphlet",
        "paper-conference",
        "patent",
        "personal_communication",
        "post-weblog",
        "post",
        "report",
        "review-book",
        "review",
        "speech",
        "thesis",
        "treaty",
        "webpage",
        "graphic",
        "song",
        "entry",
        "article",
        "book",
        "manuscript",  # putting this at the bottom because chicago-notes-bibliography doesn't render it
    ]

    TYPE_MAPPING = []

    DEFAULT = "article"

    @property
    def type(self):
        if self._formats():
            types = [self.TYPE_MAPPING.get(f) for f in self._formats()]
            for t in self.TYPE_ORDER:
                if t in types:
                    return t
        return self.DEFAULT

    def _formats(self):
        pass
