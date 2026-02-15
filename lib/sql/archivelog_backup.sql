select * from (
select distinct
        r.START_TIME START_TIME,
        r.END_TIME END_TIME,
        round(nvl(r.input_bytes/1024/1024,0), 2) INPUT_BYTES_DISPLAY,
        round(nvl(r.output_bytes/1024/1024,0), 2) OUTPUT_BYTES_DISPLAY,
        --TO_CHAR(round(r.input_bytes/1024/1024, 2),'FM999999999999990.99') INPUT_BYTES_DISPLAY,
        --TO_CHAR(round(r.output_bytes/1024/1024, 2),'FM999999999999990.99') OUTPUT_BYTES_DISPLAY,
        r.object_type INPUT_TYPE,
        r.OUTPUT_DEVICE_TYPE OUTPUT_DEVICE_TYPE,
        r.status STATUS 
from
        v$backup_piece p, v$rman_status r, v$rman_backup_job_details d
where
        r.start_time >= sysdate-:period
        and
        p.RMAN_STATUS_RECID=r.RECID
        and
        p.RMAN_STATUS_STAMP=r.STAMP
        and
        r.status like '%COMPLETED%'
        and
        r.OPERATION like '%BACKUP%'
        and
        r.object_type like 'ARCHIVE%'
        and
        d.SESSION_RECID=r.SESSION_RECID
order by
        r.START_TIME desc
) where rownum <= 7