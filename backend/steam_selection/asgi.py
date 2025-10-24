"""
ASGI config for Steam selection project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "steam_selection.settings")

application = get_asgi_application()
