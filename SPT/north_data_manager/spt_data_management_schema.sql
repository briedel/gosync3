-- Schema for SPT data management.

-- files are the information about the individual files
-- filename, checksum (SHA512), file size, disk on Primary storage,
-- disk on Copy storage
create table files (
    filenumber   INTEGER primary key autoincrement not null,
    filename     TEXT not null,
    checksum     TEXT not null,
    filesize     INTEGER not null,
    backup_nersc NUMERIC,
    backup_anl   NUMERIC,
    at_rcc       NUMERIC,
);
