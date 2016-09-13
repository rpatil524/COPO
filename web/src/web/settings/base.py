# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))


# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

LOGIN_URL = '/accounts/login/'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if os.getenv('DEBUG') == 'true' else False

ALLOWED_HOSTS = ['*']

# Django's base applications definition
DJANGO_APPS = [
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# user-defined applications definition
PROJECT_APPS = [
    'web.apps.web_copo',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.orcid',
    'allauth.socialaccount.providers.google',

    'rest_framework',
    'web.apps.chunked_upload',
    'compressor',
]

INSTALLED_APPS = DJANGO_APPS + PROJECT_APPS


# sass, social accounts...
sass_exe = '/usr/local/bin/sass'
COMPRESS_PRECOMPILERS = (
    ('text/scss', sass_exe + ' --scss  {infile} {outfile}'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # other finders..
    'compressor.finders.CompressorFinder',
)

SOCIALACCOUNT_PROVIDERS = \
    {'google':
         {'SCOPE': ['profile', 'email'],
          'AUTH_PARAMS': {'access_type': 'online'}}}


MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_tools.middlewares.ThreadLocal.ThreadLocalMiddleware',
    'web.apps.web_copo.copo_middleware.FigshareMiddleware.SetFigshareOauth'
)

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAdminUser',),
    'PAGINATE_BY': 10
}

CORS_ORIGIN_WHITELIST = (
    'http://localhost:8000',
    'http://127.0.0.1:8000'
)

ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login'

ROOT_URLCONF = 'web.urls'

import web.apps.web_copo.templates.copo
import web.apps.web_copo.templates.account

print(os.path.join(BASE_DIR, 'web', 'apps', 'web_copo', 'templates', 'copo'))

TEMPLATES = [

    {

        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here
            os.path.join(BASE_DIR, 'web', 'apps', 'web_copo', 'templates', 'copo'),
            os.path.join(BASE_DIR, 'web', 'apps', 'web_copo', 'templates', 'account'),
            os.path.join(BASE_DIR, 'allauth', 'templates', 'account'),
            os.path.join(BASE_DIR, 'allauth', 'templates', 'socialaccount')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csrf',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                # processor for base page status template tags
                "web.apps.web_copo.context_processors.get_status",
                "web.apps.web_copo.context_processors.add_partial_submissions_to_context",

                # `allauth` specific context processors
                'allauth.account.context_processors.account',
                'allauth.socialaccount.context_processors.socialaccount',
            ],
            'debug': True,
        },
    },
]

WSGI_APPLICATION = 'web.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
# STATICFILES_DIRS = (
#     '/copo/static/',
# )
# print(STATICFILES_DIRS)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
# MEDIA_ROOT = STATIC_ROOT

# MEDIA_ROOT = BASE_DIR
ELASTIC_SEARCH_URL = 'http://localhost:9200/ontologies/plant_ontology/_search'

SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 48 * 60 * 60  #


SITE_ID = 3


