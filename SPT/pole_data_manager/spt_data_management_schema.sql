-- Schema for SPT data management.

-- files are the information about the individual files
-- filename, checksum (SHA512), file size, disk on Primary storage,
-- disk on Copy storage
create table files (
    filenumber   INTEGER primary key autoincrement not null,
    filename     TEXT not null,
    checksum     TEXT not null,
    filesize     INTEGER not null,
    disk_primary TEXT not null,
    disk_copy    TEXT not null

);

-- Tasks are steps that can be taken to complete a project
create table disks (
    disknumber        INTEGER primary key autoincrement not null,
    label             TEXT not null,
    serialno          TEXT not null,
    logical_device_id TEXT not null,
    alive             NUMERIC not null,
    full              NUMERIC not null,
    max_space         INTEGER not null,
    space_used        INTEGER not null,
    previously_used   NUMERIC not null
);