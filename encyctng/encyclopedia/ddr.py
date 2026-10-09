from http import HTTPStatus
from urllib.parse import urlsplit, urlunsplit

import httpx

from . import vocab

API_BASE = 'https://ddr.densho.org/api/0.2'
DDR_OBJECTS_LIMIT = 15


def ddr_objects(title, term_id=None, limit=DDR_OBJECTS_LIMIT):
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
    return objects[:limit]


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


def get_ddrobject_embed_info(block):
    object_url = block.value['object_url']
    # interviews are out of scope for DDRObject
    if 'interview' in object_url:
        raise Exception(f"Interviews cannot be embedded: {object_url}")
    # get from API
    scheme,netloc,path,query,fragment = urlsplit(object_url)
    if (scheme != 'https') or (netloc != 'ddr.densho.org'):
        raise Exception(f"Malformed DDREmbedBlock URL: {object_url}")
    api_path = f"/api/0.2{path}"
    api_url = urlunsplit((scheme,netloc,api_path,'',''))
    r = httpx.get(api_url, timeout=3)
    if not r.status_code == HTTPStatus.OK:
        raise Exception(
            f"HTTP Error: {r.status_code} {r.reason_phrase} for {api_url}"
        )
    data = r.json()
    # only entities/objects
    if not (data.get('model')) or (data['model'] != 'entity'):
        raise Exception(f"Only objects. No collections or files: {object_url}")
    # video in general is out of scope for DDRObject
    if data.get('format') == 'av':
        raise Exception(f"Video objects cannot be embedded: {object_url}")
    # signature file with full-size download link
    signature_id = data.get('signature_id')
    file_path = f"/api/0.2/{signature_id}/"
    file_url = urlunsplit((scheme,netloc,file_path,'',''))
    r = httpx.get(file_url, timeout=3)
    if r.status_code == HTTPStatus.OK:
        fdata = r.json()
        data['links']['download'] = fdata['links']['download']
        data['size'] = fdata['size']
    # passed all the tests
    return data
