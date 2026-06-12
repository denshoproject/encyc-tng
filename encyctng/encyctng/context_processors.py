from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.core.cache import cache


def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    #base_template = request.session.get('base_template', choose_base_template(org))
    return {
        'version': settings.VERSION,
        'packages': settings.PACKAGES,
        'commit': settings.GIT_COMMIT,
        'host': os.uname()[1],
        'pid': os.getpid(),
        'time': datetime.now().isoformat(),
    }
