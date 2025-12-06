DROP DATABASE localfm;
CREATE DATABASE localfm;
DROP USER localfm;
CREATE USER localfm WITH PASSWORD 'localfm';
ALTER DATABASE localfm OWNER TO localfm;
