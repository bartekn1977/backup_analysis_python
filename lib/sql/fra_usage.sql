select
    round(space_limit/1024/1024/1024) as fra_size,
    round(100 - round((space_used - space_reclaimable)/space_limit * 100, 2), 2) as perc_free
from
    v$recovery_file_dest