from api.clients.solr_client import SolrClient, WebsiteSolrClient


async def get_onlinejournals_academic_disciplines():
    data = await SolrClient().get_onlinejournals_academic_disciplines()
    return academic_disciplines_for(data)


async def get_databases_academic_disciplines():
    data = await WebsiteSolrClient().get_databases_academic_disciplines()
    return academic_disciplines_for(
        data, plain_field="og_groups_both", delimited_field="smfield_taxonomy_delimited"
    )


def academic_disciplines_for(
    data, plain_field: str = "hlb3Str", delimited_field: str = "hlb3Delimited"
):
    def get_counts(data):
        chunked_facets = [data[i : i + 2] for i in range(0, len(data), 2)]

        counts = {}
        for facet in chunked_facets:
            counts[facet[0]] = facet[1]
        return counts

    def get_delimited_ads(data):
        return [facet.split(" | ") for facet in data if isinstance(facet, str)]

    counts = get_counts(data[plain_field])

    delimited_ads = get_delimited_ads(data[delimited_field])

    root = AcademicDiscipline(name="root", count=0)

    for delimited_ads in delimited_ads:
        current = root
        for ad in delimited_ads:
            if ad not in current.disciplines:
                new_ad = AcademicDiscipline(name=ad, count=counts[ad])
                current.disciplines.append(new_ad)
                current = new_ad
            else:
                current = current.get_subdiscipline(ad)

    return root.disciplines


class AcademicDiscipline:
    def __init__(self, name, count):
        self.name = name
        self.count = count
        self.disciplines = []

    def get_subdiscipline(self, d):
        index = self.disciplines.index(d)
        return self.disciplines[index]

    def __eq__(self, other):
        return other == self.name

    def __ne__(self, other):
        return other != self.name

    def __repr__(self):
        return self.name
