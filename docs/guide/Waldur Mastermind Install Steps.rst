**************************************
CentOS Waldur Mastermind Install Steps
**************************************

1. Update system and set root password

.. code-block:: shell

    sudo yum update
    sudo passwd
    su – root

2. Install Dependencies

.. code-block:: shell
    
    yum groupinstall "Development tools"
    sudo yum install python3-pip git redis gcc libffi-devel openssl-devel postgresqldevel libjpeg-devel zlib-devel python3-devel xmlsec1 xz-devel openldap-devel

3. Start Redis server

.. code-block:: shell
    
    sudo systemctl start redis
    sudo systemctl enable redis


4. Install Python 3.8

.. code-block:: shell
    
    sudo dnf install gcc openssl-devel bzip2-devel libffi-devel
    cd /opt
    wget https://www.python.org/ftp/python/3.8.6/Python-3.8.6.tgz
    tar xzf Python-3.8.6.tgz
    cd Python-3.8.6
    sudo ./configure --enable-optimizations
    sudo make altinstall

5. Install pip and poetry

.. code-block:: shell
    
    python3.8 -m pip install --upgrade pip
    python3.8 -m pip install poetry

6. Install hiredis and virtualenv

.. code-block:: shell
    
    pip3.8 install hiredis
    pip3.8 install testresources
    pip3.8 install virtualenv
    poetry config virtualenvs.create false

7. Clone waldur mastermind repo

.. code-block:: shell
   
   git clone https://github.com/opennode/waldur-mastermind.git
   cd waldur-mastermind

8. Install poetry

.. code-block:: shell
    
    poetry install --no-dev9. Setup settings.py
    cp src/waldur_core/server/settings.py.example src/waldur_core/server/settings.py

9. Copy secret key by running

.. code-block:: shell
    
    head -c32 /dev/urandom | base64

10. Edit settings.py. Add secret key and edit database settings
(https://docs.djangoproject.com/en/1.11/ref/settings/#databases)

.. code-block:: shell
    
    sudo nano src/waldur_core/server/settings.py

11. Install PostgreSQL

.. code-block:: shell
    
    sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-
    x86_64/pgdg-redhat-repo-latest.noarch.rpm
    sudo dnf -qy module disable postgresql
    sudo dnf install -y postgresql13-server
    sudo /usr/pgsql-13/bin/postgresql-13-setup initdb
    sudo systemctl enable postgresql-13


12. Setup psql user and create waldur user

.. code-block:: shell
    
    sudo -u postgres psql
    CREATE USER root;
    ALTER USER root SUPERUSER CREATEDB;
    CREATE USER waldur WITH PASSWORD ‘waldur’;
    \q

13. Create waldur database

.. code-block:: shell
    
    createdb waldur

14. Compile messages

.. code-block:: shell
    
    django-admin compilemessages

15. Make waldur static file directory

.. code-block:: shell
    
    mkdir -p /usr/share/waldur/static

16. Create tmp_settings.py file

.. code-block:: shell
    
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

17. Collect static files from tmp_settings.py

.. code-block:: shell
    
    PYTHONPATH="${PYTHONPATH}:/usr/src/waldur" django-admin collectstatic --noinput --
    settings=tmp_settings19. Migrate files
    poetry run waldur migrate --noinput

18. Collect waldur static files

.. code-block:: shell
    
    poetry run waldur collectstatic --noinput

19. Run waldur server

.. code-block:: shell
    
    poetry run waldur runserver
