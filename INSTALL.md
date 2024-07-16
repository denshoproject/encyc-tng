## Database Setup

``` bash
ssh DATABASE_SERVER
sudo su - postgres
```
``` sql
CREATE DATABASE encyctng;
CREATE USER encyctng WITH PASSWORD 'REDACTED';
ALTER DATABASE encyctng OWNER TO encyctng;
\connect encyctng;
GRANT CREATE ON SCHEMA public TO encyctng;
\q
```
