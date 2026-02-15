select
    distinct
    pdb.pdb_name,
    df.tablespace_name tablespace_name,
    df.files_no files_no,
    round(nvl(totalusedspace,0)) used,
    round(df.totalspace - nvl(tu.totalusedspace,0)) free,
    round(nvl(df.totalspace,0)) total,
    --round( 100 * ( (df.totalspace - nvl(tu.totalusedspace,0))/ df.totalspace),2) perc_free,
    round(100 - round( 100 * ( (nvl(tu.totalusedspace,0))/ decode(df.maxspace,0,df.totalspace,df.maxspace)),2),2) perc_free,
    round(nvl(df.maxspace,0)) max_file
from
    (
        select
            con_id,
            tablespace_name,
            count(file_id) files_no,
            round(sum(bytes) / 1048576) TotalSpace,
            sum(decode(AUTOEXTENSIBLE,'YES',maxbytes,'NO',bytes))/1024/1024 maxspace
        from
            cdb_data_files 
        group by
            con_id, tablespace_name
    ) df,
    (
        select
            con_id,
            tablespace_name,
            round(sum(bytes)/(1024*1024)) totalusedspace
        from
            cdb_segments 
        group by
            con_id, tablespace_name
    ) tu,
    (
        select
            con_id,
            tablespace_name,
            round(sum(bytes)/1024/1024 ,2) as free_space
        from
            cdb_free_space
        group by
            con_id, tablespace_name
    ) fs,
    cdb_pdbs pdb
where
    df.tablespace_name = tu.tablespace_name(+)
    AND
    df.tablespace_name = fs.tablespace_name(+)
    AND
    pdb.PDB_ID = df.con_id
ORDER BY
    1, 4 desc