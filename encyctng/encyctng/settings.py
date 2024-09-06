"""
Django settings for encyctng project.

Generated by 'django-admin startproject' using Django 5.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import configparser
from pathlib import Path
import sys

# Build paths inside the project like this: BASE_DIR / PATH
PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# User-configurable settings are located in the following files.
# Files appearing *later* in the list override earlier files.
CONFIG_FILES = [
    '/etc/encyc/encyctng.cfg',
    '/etc/encyc/encyctng-local.cfg'
]
config = configparser.ConfigParser()
configs_read = config.read(CONFIG_FILES)
if not configs_read:
    print(f'Cannot read config files! {CONFIG_FILES}')
    sys.exit(1)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config.get('security', 'secret_key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config.get('debug', 'debug')

ALLOWED_HOSTS = [
    host.strip()
    for host in config.get('security', 'allowed_hosts').strip().split(',')
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    host.strip()
    for host in config.get('security', 'csrf_origins').strip().split(',')
    if host.strip()
]

CACHE_TIMEOUT = 60 * 15
CACHE_TIMEOUT_LONG = 60 * 60 * 12

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'modelcluster',
    'taggit',
    'wagtail',
    'wagtail.admin',
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.documents',
    'wagtail.embeds',
    'wagtail.images',
    'wagtail.search',
    'wagtail.sites',
    'wagtail.snippets',
    'wagtail.users',
    'wagtailmedia',
    #
    'home',
    'editors',
    'encyclopedia',
    'search',
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
    'encyclopedia.middleware.RedirectLegacyURLsMiddleware',
]

ROOT_URLCONF = 'encyctng.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            PROJECT_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'encyctng.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql",
        'NAME': config.get('database', 'name'),
        'HOST': config.get('database', 'host'),
        'PORT': config.get('database', 'port'),
        'USER': config.get('database', 'username'),
        'PASSWORD': config.get('database', 'password'),
    }
}

REDIS_HOST = '127.0.0.1'
REDIS_PORT = '6379'
REDIS_DB_CACHE = '10'

CACHES = {
    "default": {
        #'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_CACHE}",
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATICFILES_DIRS = [
    PROJECT_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'static'
STATIC_URL = '/static/'

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Default storage settings, with the staticfiles storage updated.
# See https://docs.djangoproject.com/en/5.0/ref/settings/#std-setting-STORAGES
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    # ManifestStaticFilesStorage is recommended in production, to prevent
    # outdated JavaScript / CSS assets being served from cache
    # (e.g. after a Wagtail upgrade).
    # See https://docs.djangoproject.com/en/5.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
    },
}


# Wagtail settings

WAGTAIL_SITE_NAME = 'Densho Encyclopedia'

# Search
# https://docs.wagtail.org/en/stable/topics/search/backends.html
WAGTAILSEARCH_BACKENDS = {
    'default': {
        'BACKEND': 'wagtail.search.backends.database',
    }
}

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash
WAGTAILADMIN_BASE_URL = config.get('wagtail', 'base_url'),

# Allowed file extensions for documents in the document library.
# This can be omitted to allow all files, but note that this may present a security risk
# if untrusted users are allowed to upload files -
# see https://docs.wagtail.org/en/stable/advanced_topics/deploying.html#user-uploaded-files
WAGTAILDOCS_EXTENSIONS = [
    'csv', 'docx', 'key', 'odt', 'pdf', 'pptx', 'rtf', 'txt', 'xlsx', 'zip',
]
