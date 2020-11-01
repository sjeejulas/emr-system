#  Medidata Django App

#  Install Database

You can do following this [link](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-18-04)

**Step 1:** Install PostgreSQL

**Step 2:** Create user and database on PostgreSQL

#  How to Setup Django App

**Step 1:** git clone this repo

**Step 2:** cd to the cloned repo

**Step 3:** install python library with `pip install -r config/requirements.txt`

**Step 4:** setup user and database in settigs **medi/settings/local_settings.py**

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'medi',
        'USER': 'medi',
        'PASSWORD': 'medi',
        'HOST': '',
    }
}
```

**Step 5:** migrate database with `python manage_local.py migrate`

#  Initial Data

**psql -U [USER] [DATABASE] < initial_data/initial.sql**


#  Run Django App

**python manage_local.py runserver**
