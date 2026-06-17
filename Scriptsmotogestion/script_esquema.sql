connect system/123

show con_name

ALTER SESSION SET CONTAINER=CDB$ROOT;
ALTER DATABASE OPEN;

DROP TABLESPACE ts_ppi INCLUDING CONTENTS and DATAFILES;
    
CREATE TABLESPACE ts_ppi LOGGING
DATAFILE 'C:\nada\DF_ppi.dbf' size 4 M
extent management local segment space management auto; 
 
alter session set "_ORACLE_SCRIPT"=true; 
 
drop user us_ppi cascade;
    
CREATE user us_ppi profile default 
identified by 123
default tablespace ts_ppi 
temporary tablespace temp 
account unlock;     

grant connect, resource,dba to us_ppi; 

connect us_ppi/123

show user

