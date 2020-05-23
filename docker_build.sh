# Installing Python package manager
pip3 install poetry
poetry config virtualenvs.create false

# Install Python dependencies for Waldur MasterMind from PyPI
poetry install --no-dev

# Compile i18n messages
cp packaging/settings.py src/waldur_core/server/settings.py
django-admin compilemessages

# Build static assets
mkdir -p /usr/share/waldur/static
cat > tmp_settings.py << EOF
# Minimal settings required for 'collectstatic' command
INSTALLED_APPS = (
    'admin_tools',
    'admin_tools.dashboard',
    'admin_tools.menu',
    'admin_tools.theming',
    'fluent_dashboard',  # should go before 'django.contrib.admin'
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'jsoneditor',
    'waldur_core.landing',
    'rest_framework',
    'rest_framework_swagger',
    'django_filters',
)
SECRET_KEY = 'tmp'
STATIC_ROOT = '/usr/share/waldur/static'
STATIC_URL = '/static/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['waldur_core/templates'],
        'OPTIONS': {
            'context_processors': (
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # required by django-admin-tools >= 0.7.0
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
            ),
            'loaders': (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'admin_tools.template_loaders.Loader',  # required by django-admin-tools >= 0.7.0
            ),
        },
    },
]
EOF
PYTHONPATH="${PYTHONPATH}:/usr/src/waldur" django-admin collectstatic --noinput --settings=tmp_settings

# Copy template files to in-docker storage

# Copy configuration files
mkdir -p /etc/waldur-templates/
cp packaging/etc/waldur/celery.conf /etc/waldur-templates/celery.conf
cp packaging/etc/waldur/core.ini /etc/waldur-templates/core.ini
cp packaging/etc/waldur/uwsgi.ini /etc/waldur-templates/uwsgi.ini

# Copy default SAML2 configuration
mkdir -p /etc/waldur-templates/saml2/
cp packaging/etc/waldur/saml2.conf.py.example /etc/waldur-templates/saml2/
