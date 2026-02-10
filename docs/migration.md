# Migrating Densho Encyclopedia data to `encyc-tng`


All of these examples assume you have become the user `encyc`, are in the `encyc-tng` directory, and you have activated the Python virtual environment:
``` bash
cd /opt/encyc-tng
sudo su encyc
source venv/encyctng/bin/activate
```


## API Credentials

Check `/etc/hosts` to see that `encycpsms.local` is pointed to `packrat`, and make sure `/etc/encyc/core-local.cfg` has the following filled in.
``` ini
[mediawiki]
scheme=http
host=encycmw.local
username=REDACTED
password=REDACTED

[sources]
api_url=http://encycpsms.local/api/2.0
api_username
api_password
api_htuser
api_htpass
```


## Download metadata and Primary Sources binaries to local

Log in to `packrat` as `encyc` and dump data for the `sources` app:
```
cd /opt/encyc-psms
python psms/manage.py dumpdata sources --format=jsonl > /tmp/encycpsms-sources-20260210-1544.jsonl
```
Copy it to the `encyc-tng-data` repo, commit, etc. git-pull to the destination system.

Make a directory for migration data:
``` bash
mkdir -p /opt/encyc-tng/data/sources/
```

Copy binary files from PSMS.  Before you do this, make sure you have 4.8G free space. Or consider not doing it...
``` bash
rsync -avz ansible@192.168.0.24:/var/www/encycpsms/media/sources /opt/encyc-tng/data/
```
Download Primary Source metadata from the API:
``` python
jsonl_path = '/opt/encyc-tng/data/densho-psms-sources.jsonl'
from encyclopedia.migration import Sources
sources = [source for source in Sources.load_psms_sources_api().values()]
Sources.save_psms_sources_jsonl(sources, jsonl_path)
```

mkdir -p /opt/encyc-tng/data/articles
Copy file of authors' alternative names in `/opt/encyc-tng/data/author-alts.txt`.
Copy file of article redirects in in `/opt/encyc-tng/data/`.
Download Articles data from the wiki:
``` python
from encyclopedia import migration
from encyc import wiki
basedir = '/opt/encyc-tng/data'
migration.Articles.download_articles(wiki.MediaWiki(), basedir)
```

Copy current list of redirects from [the Editors' MediaWiki](https://editors.densho.org/index.php?title=Special:ListRedirects&limit=500&offset=0) and paste into `/opt/encyc-tng/data/redirects-raw.txt`. Then run the `process_redirects` function.
```
from pathlib import Path
from encyclopedia import migration
basedir = Path('/opt/encyc-tng/data')
migration.Articles.process_redirects(basedir)
```


## Static media

``` bash
python encyctng/manage.py collectstatic
```


## Resetting the database

### PostgreSQL

Delete all tables, then drop the database and create a new one.  Substitute your chosen password for `REDACTED` in the `CREATE USER` statement
``` sql
DO $$ DECLARE
    r RECORD;
BEGIN
    -- if the schema you operate on is not "current", you will want to
    -- replace current_schema() in query with 'schematodeletetablesfrom'
    -- *and* update the generate 'DROP...' accordingly.
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;
DROP DATABASE encyctngdev;
CREATE DATABASE encyctngdev;
CREATE USER encyctng WITH PASSWORD 'REDACTED';
ALTER DATABASE encyctngdev OWNER TO encyctng;
\connect encyctngdev;
GRANT CREATE ON SCHEMA public TO encyctng;
\q
```

If you're doing this a lot or trying to speedrun you can do it in two lines:
```
DROP DATABASE encyctng; CREATE DATABASE encyctng; ALTER DATABASE encyctng OWNER TO encyctng;
\connect encyctngdev; GRANT CREATE ON SCHEMA public TO encyctng; \q
```

Run Django commands to setup a fresh database:
``` bash
python encyctng/manage.py migrate
python encyctng/manage.py createsuperuser
```

### SQLite3

With SQLite3 you just delete the database file and set up a new one:
``` bash
# as encyc
rm db/encyctng.sqlite3
python encyctng/manage.py migrate
python encyctng/manage.py createsuperuser
```


## Initial Setup

Create a Site object with the URL and set it as default. Reset the `localhost` site to not be the default.
``` python
HOSTNAME = 'encyclopedia.densho.org'
```
``` python
SITE_NAME = 'Densho Encyclopedia'
site = Site(hostname=HOSTNAME, site_name=SITE_NAME, root_page=Page.objects.get(title='Home'), is_default_site=True)
site.save()
localhost = Site.objects.get(hostname='localhost')
localhost.is_default_site = False
localhost.save()
```

This creates things like the "Encyclopedia" page at the top of the `Articles` hierarchy and the `Collection` objects that the various types of Primary Sources will be added to.

Export usernames/passwords as an environment var:
``` bash
export TNGUSERS="USER1:REDACTED;USER2:REDACTED;..."
```
``` python
from pathlib import Path
from encyclopedia import migration
basedir = Path('/opt/encyc-tng/data')
migration.initial_setup(basedir)
```
Remember to edit `.bash_history` afterwards to remove those passwords.

## Authors

``` python
from encyclopedia import migration
basedir = '/opt/encyc-tng/data'
migration.Authors.import_authors(basedir, debug=True)
```

## Primary Sources

Clear old media files:
```
rm -Rf /var/www/encyctng/media/documents/*
rm -Rf /var/www/encyctng/media/images/*
rm -Rf /var/www/encyctng/media/media/*
rm -Rf /var/www/encyctng/media/media_thumbnails/*
rm -Rf /var/www/encyctng/media/original_images/*
```

Load metadata and import Primary Sources:
``` python
from pathlib import Path
from encyclopedia import migration
basedir = Path('/opt/encyc-tng/data')
sources_jsonl = Path('/opt/encyc-tng/data/densho-psms-sources.jsonl')
sources_dir = sources_jsonl.parent
sources_collection,sources_by_headword,source_pks_by_filename = migration.Articles.load_sources(basedir, sources_jsonl)
# import all
result = migration.Sources.import_sources(sources_by_headword, sources_dir)
```
```# import title
result = migration.Sources.import_sources(sources_by_headword, sources_dir, title='Manzanar')
```

Load data from old `encycpsms.sources` app:
```
python encyctng/manage.py loaddata data/sources-encycpsms-20260210-1544.jsonl --app=sources
```


## Articles

Load article data and import:
``` python
user = User.objects.get(username='gjost')
jsonl_path = '/opt/encyc-tng/data/densho-psms-sources.jsonl'
from pathlib import Path
from encyclopedia import migration
basedir = Path('/opt/encyc-tng/data')
migration.Articles.import_articles(basedir, jsonl_path, user=user)
```

And then rewrite internal URLs
```
from pathlib import Path
from encyclopedia import migration
basedir = Path('/opt/encyc-tng/data')
redirects = migration.Articles.load_redirects(basedir)
migration.Articles.rewrite_article_urls(redirects)
```

Report unconverted internal URLs
```
unconverted_urls_path = '/tmp/unconverted-article-urls.csv'
migration.Articles.unconverted_article_urls(csvpath=unconverted_urls_path)
```

Report remaining unused Sources
```
sources_remaining_json_path = '/tmp/sources-by-headword-remaining.jsonl'
from encyclopedia import migration
migration.Articles.report_sources_remaining(sources_remaining_json_path)
```

Report comparing published articles on encycfront and encyctng
```
from encyclopedia import migration
migration.Articles.report_compare_published()
```

Report comparing PSMS sources and TNG sources
- login to psms.densho.org
- copy URL: https://psms.densho.org/api/2.0/sources/?format=json
- save page to file: /tmp/sources-psms.json
- scp that file to encyctng vm: /tmp/sources-psms.json
```
sources_psms_path = '/tmp/sources-psms.json'
from encyclopedia import migration
migration.Sources.report_compare_published(sources_psms_path)
```

Collect reports and make browseable
```
# make folder for this run and collect .csv files in folder
export RIGHTNOW=`date +"%Y%m%d-%H%M"`
export DESTDIR="/var/www/encyctng/media/migration/reports/$RIGHTNOW"
mkdir $DESTDIR
cp /tmp/*.csv $DESTDIR
```


## Post-Migration Manual Tasks