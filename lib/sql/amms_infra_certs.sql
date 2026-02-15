select * from (
select module, file_name, expiration_date from amms_infra.certs order by 1, 2
) where rownum <= 10