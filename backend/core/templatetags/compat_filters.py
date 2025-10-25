"""
Compatibility template filters for third-party admin skins.
"""

from django import template

register = template.Library()


@register.filter(name="length_is")
def length_is(value, arg):
    """
    Reintroduce the legacy ``length_is`` filter removed in Django 5.
    Returns True when the length of ``value`` equals ``arg``.
    """

    try:
        return len(value) == int(arg)
    except (TypeError, ValueError):
        return False
