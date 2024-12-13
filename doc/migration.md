# Migrating Densho Encyclopedia data to `encyc-tng`


All of these examples assume you have become the user `encyc`, are in the `encyc-tng` directory, and you have activated the Python virtual environment:
``` bash
cd /opt/encyc-tng
sudo su encyc
source venv/encyctng/bin/activate
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
DROP DATABASE encyctng;
CREATE DATABASE encyctng;
CREATE USER encyctng WITH PASSWORD 'REDACTED';
ALTER DATABASE encyctng OWNER TO encyctng;
\connect encyctng;
GRANT CREATE ON SCHEMA public TO encyctng;
\q
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


## Authors
``` python
from encyclopedia.migration import Authors
Authors.import_authors(debug=True)
```


## Primary Sources

*THIS SECTION IS INCOMPLETE!*

Source migration needs to happen on same machine as the binaries.
Also the Sources API is a pain so download and write to a file
``` bash
mkdir /opt/encyc-tng/data/
mkdir /opt/encyc-tng/data/sources/
```

(as encyc) Load PrimarySource data from PSMS API:
``` python
from encyclopedia.migration import Sources
sources = [source for source in Sources.load_psms_sources_api().values()]
Sources.save_psms_sources_jsonl(sources, '/tmp/densho-psms-sources-YYYYMMDD.jsonl')
```
(as user) and write to JSONL file:
``` bash
cp /tmp/densho-psms-sources-YYYYMMDD.jsonl /opt/encyc-tng/data/
```
Copy binary files from PSMS.  Before you do this, make sure you have 4.8G free space. Or consider not doing it...
``` bash
rsync -avz ansible@packrat:/var/www/encycpsms/media/sources/* data/sources/
```


``` python
jsonl_path = '/opt/encyc-tng/data/densho-psms-sources-YYYYMMDD.jsonl'
from pathlib import Path
from encyclopedia.migration import Sources
jsonl_path = Path(jsonl_path)
sources_dir = jsonl_path.parent
primary_sources = Sources.load_psms_sources_jsonl(jsonl_path)
# just one for now
primary_sources = primary_sources[:1]
# import
Sources.import_sources(primary_sources, sources_dir)
```


## Articles
``` python
from encyclopedia.migration import Articles
Articles.import_articles(debug=True, dryrun=False)
```
