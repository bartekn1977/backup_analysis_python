select
    'Lb. rekordow' as lb,
    (select to_char(count(1), 'fm999,999,999,990') from sysadm.log_zapisy_akt) akt_records,
    (select to_char(count(1), 'fm999,999,999,990') from sysadm.log_zapisy_arch) arch_records
from
dual