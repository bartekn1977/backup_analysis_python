select
    (select round(sum(bytes)/1024/1024/1024, 2) size_in_gb from dba_data_files) as phys_size,
    (select round(sum(bytes)/1024/1024/1024,2) size_in_gb from dba_segments) as data_size 
from
dual 