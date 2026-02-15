select
    (
        select sum(size_in_gb) from (
            select round(sum(bytes)/1024/1024/1024, 2) size_in_gb from v$datafile
            union
            select round(sum(bytes)/1024/1024/1024, 2) from v$tempfile
        )
    ) as phys_size,
    (select round(sum(bytes)/1024/1024/1024,2) size_in_gb from CDB_SEGMENTS) as data_size 
from
dual 