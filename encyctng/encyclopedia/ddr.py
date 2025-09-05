from http import HTTPStatus

import httpx

from . import vocab

API_BASE = 'https://ddr.densho.org/api/0.2'


def ddr_objects(title, term_id=None):
    """DDR objects associated with article

    Data comes from densho-vocab/.../topics.json
    Each topic term has an "encyc_urls" list.
    The term ID is used to
    Each DDR topic has a list of Encyclopedia article titles
    """
    missing_term_ids = [
        0, 13, 30, 39, 41, 55, 58, 60, 64, 77, 79, 83, 105, 112, 119, 121,
        122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135,
        136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 159, 182, 184, 201, 205
    ]
    # TODO cache this
    if term_id:
        # support demo code for now
        terms = [{'id':term_id}]
    else:
        terms = vocab.Topics().article_terms(title)
    objects = []
    for term in terms:
        url = f"{API_BASE}/facet/topics/{term['id']}/objects/?format=json"
        data = httpx.get(url, timeout=3).json()
        for o in data['objects']:
            objects.append(o)
    return objects


#def objects_for_title(title: str) -> list:
#    # TODO parallelize
#    objects = []
#    for term_id in vocab.Topics.terms(title):
#        objects += APITopic.get_objects(term_id)
#    # scrub extraneous fields
#    fields = ['id', 'links', 'title', 'description']
#    for object in objects:
#        object_keys = [key for key in object.keys()]
#        for fieldname in object_keys:
#            if fieldname not in fields:
#                object.pop(fieldname)
#    # TODO now cache
#    return objects


#class APITopic():
#
#    def get_objects(term_id=None):
#        url = f"{API_BASE}/facet/topics/{term_id}/objects/?format=json"
#        response = httpx.get(url)
#        if HTTPStatus(response.status_code).is_success:
#            return response.json()['objects']
#        return []
