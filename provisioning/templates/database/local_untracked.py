# Database
DATABASES = {
    'default': {
        'ENGINE':'django.db.backends.postgresql_psycopg2',
        'NAME': '{{ db_name }}',
        'USER': '{{ db_username }}',
        'PASSWORD': '{{ db_password }}',
        'HOST': '{{ db_host }}',
        'PORT': '{{ db_port }}',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "{{ seed_cache_name }}:6379",
        'OPTIONS': { 'DB': 1 },
        'TIMEOUT': 300
    }
}
BROKER_URL = 'redis://{{ seed_cache_name }}:6379/1'
