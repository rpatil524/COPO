# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from tools import resolve_env

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCHEMA_DIR = os.path.join(BASE_DIR, 'web', 'apps', 'web_cop', 'schemas')

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = resolve_env.get_env('SECRET_KEY')

LOGIN_URL = '/accounts/auth/'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if resolve_env.get_env('DEBUG') == 'true' else False

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
    'web.apps.web_copo.rest',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.orcid',
    # 'web.apps.web_copo',
    'rest_framework',
    'chunked_upload',
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

# MIDDLEWARE_CLASSES = (
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
#     'django_tools.middlewares.ThreadLocal.ThreadLocalMiddleware',
#     'web.apps.web_copo.copo_middleware.FigshareMiddleware.SetFigshareOauth',
#     'web.apps.web_copo.copo_middleware.OrcidMiddleware.OrcidOAuth'
# )


MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_tools.middlewares.ThreadLocal.ThreadLocalMiddleware',
    # 'web.apps.web_copo.copo_middleware.FigshareMiddleware.SetFigshareOauth',
    # 'web.apps.web_copo.copo_middleware.OrcidMiddleware.OrcidOAuth',
]


AUTHENTICATION_BACKENDS = (
    # Needed to auth by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as auth by e-mail
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

ACCOUNT_LOGOUT_REDIRECT_URL = '/copo/login'

ROOT_URLCONF = 'web.urls'

LOGIN_URL = '/copo/login'

TEMPLATES = [

    {

        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here

            os.path.join(BASE_DIR, 'web', 'landing'),
            os.path.join(BASE_DIR, 'web', 'apps', 'web_copo', 'templates', 'copo'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
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

                'django.contrib.auth.context_processors.auth',
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

MEDIA_ROOT = os.path.join(BASE_DIR, resolve_env.get_env('MEDIA_PATH'))

ELASTIC_SEARCH_URL = 'http://localhost:9200/ontologies/plant_ontology/_search'

SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 48 * 60 * 60  #

SITE_ID = 1

COPO_URL = 'copo-project.org'

DATAVERSE = {
    "TEST_DATAVERSE_API_URL": "https://apitest.dataverse.org//api/v1",
    "TEST_DATAVERSE_SERVICE": "/dvn/api/data-deposit/v1.1/swordv2/",
    "TEST_DATAVERSE_API_TOKEN": "06745d26-1684-489d-a87b-52df9ba05375",
    "HARVARD_TOKEN": "ea9a511b-d8ae-49ee-9614-9fe131dd8f5f",
    "HARVARD_TEST_API": "https://demo.dataverse.org/api/v1/",
    "HARVARD_TEST_TOKEN": "227bc74d-088f-423f-8f49-d8503f62f7de"
}
