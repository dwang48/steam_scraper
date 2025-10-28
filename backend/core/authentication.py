"""
Custom authentication helpers for the Steam selection API.
"""

from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session authentication that skips CSRF enforcement for API clients."""

    def enforce_csrf(self, request):
        return

