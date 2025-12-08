# LocalFM

My personal music nexus.

## Local deployment

### Windows

```shell
scoop install postgresql

# initialise the DB data dir
d:\scoop\apps\postgresql\current\bin\initdb.exe -D D:\scoop\persist\postgresql\18.1\data -E 'UTF-8' --lc-collate='English_Ireland.UTF-8' --lc-ctype='English_Ireland.UTF-8'
```

### Linux

```shell
sudo apt install postgresql-server

/usr/lib/postgresql/17/bin/initdb -D ./deployment/local/pgdata -E 'UTF-8' --lc-collate='en_IE.UTF-8' --lc-ctype='en_IE.UTF-8'
```
