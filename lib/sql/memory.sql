select
    (select c.MAX_SIZE/1024/1024/1024 as size_in_gb from v$memory_dynamic_components c  where component like 'SGA%') as sga,
    (select c.MAX_SIZE/1024/1024/1024 as size_in_gb from v$memory_dynamic_components c  where component like 'PGA%') as pga
FROM
dual