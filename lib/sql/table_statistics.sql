select a.TABLE_NAME, a.OWNER, to_char(b.max_date, 'YYYY-MM-DD HH:MI:SS') from (
select TABLE_NAME, OWNER, MIN(STATS_UPDATE_TIME) min_date from all_tab_stats_history where OWNER not in ('DBSNMP','SYSMAN') group by TABLE_NAME, OWNER
) a,
(
select TABLE_NAME, OWNER, MAX(STATS_UPDATE_TIME) max_date from all_tab_stats_history where OWNER not in ('DBSNMP','SYSMAN') group by TABLE_NAME, OWNER
) b
where a.TABLE_NAME = b.TABLE_NAME
order by 3
fetch first 10 rows only