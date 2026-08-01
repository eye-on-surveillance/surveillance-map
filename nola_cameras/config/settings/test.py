"""
Test settings — used by CI and local test runs.

Skips dev-only apps (debug_toolbar, django_extensions) so tests
don't require optional dependencies.
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# Faster password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Skip whitenoise compression in tests
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
