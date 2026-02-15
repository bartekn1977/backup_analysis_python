select * from (
select
a.FILE_NAME,
round(a.bytes/1024/1024/1024,2) as Used_GB,
round(a.MAXBYTES/1024/1024/1024,2) as Max_Gb,
b.LOWER,
b.HIGHEST,
round(LAST_DAY(to_date(b.HIGHEST,'YYYY-MM'))-SYSDATE,0) as test_period
from
sys.dba_data_files a,
LOBADM.PARTITIONS b,
sys.dba_tablespaces c
where
a.tablespace_name = b.TABLENAME||'_S'
and
a.tablespace_name = c.tablespace_name
order by b.HIGHEST desc
) where rownum <= 1