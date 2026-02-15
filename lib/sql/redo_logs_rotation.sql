select * from (
    select count(*) as rotation, to_char(first_time,'YYYY-MM-DD HH24') as day_hour from gv$log_history group by to_char(first_time,'YYYY-MM-DD HH24') order by 1 desc
) where rownum <= 5