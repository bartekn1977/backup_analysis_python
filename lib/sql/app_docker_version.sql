select
    distinct decode(a.SYS_NAME, 'EDM', 1, 'MPI', 2, 'ACS', 3, 'LOB', 4, 'DICT', 5, 'LOG', 6, 'PARAM', 7, 'COM', 8, 99) as lp,
    a.SYS_NAME as component_name,
    a.SYS_VER as component_ver,
    a.WHEN_INSERTED as component_instal_date
from
    ASSECOSYSTEM.SYSTEMS a,
    (
        select SYS_NAME, max(WHEN_INSERTED) as WHEN_INSERTED from ASSECOSYSTEM.SYSTEMS group by SYS_NAME
    ) b
where
    a.SYS_NAME = b.SYS_NAME
    and
    a.WHEN_INSERTED = b.WHEN_INSERTED 
order by 1