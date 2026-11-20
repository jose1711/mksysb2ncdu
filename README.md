# mksysb2ncdu

See what takes up space in an AIX **mksysb** (or **savevg**) image using [ncdu](https://dev.yorhel.nl/ncdu),
without restoring it.

`mksysb2ncdu` reads the backup and writes an ncdu JSON export. ncdu can read that export from a file
or straight from a pipe:

```sh
mksysb2ncdu host.mksysb | ncdu -r -f-
```

## Features

- Streams the backup in a single pass, reading only headers. File data is skipped, nothing is
  unpacked or written to disk. A 1.5 GB mksysb converts in under a second on Linux.
- Reads from a file or from stdin, so the image can come over `ssh`, from `zcat`, `dd` and so on.
- Runs on Linux and on AIX itself (`/usr/bin/python3`). Single file, Python 3 standard library only.
- Reports apparent size, size rounded to JFS2 blocks, or the space each file takes **inside the
  mksysb** (after packing, with headers): `--dsize archive`.
- Exports owner, group, mode and mtime too (shown in ncdu with `-e` / extended mode).
- Finds the start of the backup when something precedes it, e.g. a whole tape image copied into
  one file.

## Usage

```sh
# local file
mksysb2ncdu host.mksysb | ncdu -r -f-

# image stored on an AIX host, browsed on Linux (the whole image goes over the network)
ssh aix 'cat /mksysb/host.mksysb' | mksysb2ncdu | ncdu -r -f-

# much faster: convert on AIX, transfer only the small JSON
ssh aix 'mksysb2ncdu /mksysb/host.mksysb' | ncdu -r -f-

# save the export for later
mksysb2ncdu host.mksysb -o host.ncdu
ncdu -r -f host.ncdu

# what makes the mksysb itself so big?
mksysb2ncdu --dsize archive host.mksysb | ncdu -r -f-

# a directory tree backed up by name, no archive file needed (on AIX)
find /data -print | backup -iqf - | mksysb2ncdu --root /data | ncdu -r -f-
```

ncdu for AIX is available from the [AIX Toolbox](https://www.ibm.com/support/pages/aix-toolbox-open-source-software-overview):
`dnf install ncdu`.

### Options

```
mksysb2ncdu [-h] [-o OUTPUT] [--dsize {block,archive,apparent}] [--block BLOCK]
            [--root ROOT] [--scan MB] [-q] [file]

  file                  mksysb file or - for stdin (default)
  -o, --output OUTPUT   output file (default stdout)
  --dsize {block,archive,apparent}
                        what to report as disk usage: block = size rounded up
                        to --block (default), archive = space taken in the
                        mksysb itself (after packing, with headers),
                        apparent = file size
  --block BLOCK         block size for --dsize=block (default 4096, JFS2)
  --root ROOT           name of the root directory shown in ncdu (default /)
  --scan MB             how many MB to search for the start of the backup
                        (tape image), default 256
  -q, --quiet           no progress or warnings on stderr
```

## Installation

Copy `mksysb2ncdu` to a directory in your `PATH` and make it executable:

```sh
install -m 755 mksysb2ncdu ~/.local/bin/     # Linux
cp mksysb2ncdu /usr/local/bin/ && chmod 755 /usr/local/bin/mksysb2ncdu   # AIX
```

It needs Python 3.5 or newer and nothing else.

## Limitations

- **Hard links are counted once per name.** `backup` by name stores the full data under every
  name and writes a dummy inode number (`0xffffffff`), so the archive has no way to tell that two
  names are the same file.
- **Sockets never show up**, because mksysb/backup does not archive them.
- **Sparse files** are reported at their full size: the archive does not record holes.
- Only the "backup by name" format (mksysb, savevg, `backup -i`) is supported. By-inode backups
  (`backup -0 /fs`) use a different layout.
- Multi-volume backups were not tested.

## Format notes

The format is described by `/usr/include/dumprestor.h` on AIX. In short:

- Every record starts with `struct hdr`: length in 8-byte words, type, magic `60011` (`60012` = data
  packed with Huffman `pack`), checksum. **Headers are little-endian**, even though AIX is big-endian.
- `FS_VOLUME` (0) starts the backup (`"by name"`, date, user).
- Each file is described by `FS_NAME_X` (11), `FS_NAME_LF` (12, 64-bit sizes for files over 2 GB) or
  `FS_NAME_E` (15). Each of these holds nlink, mode, uid, gid, size, times, the packed size and the
  path (`./usr/bin/ls`).
- For types 11 and 12, except symlinks, the header is followed by `struct sac_rec` (ACL and PCL
  sizes in words) and the ACL/PCL data.
- Next come the file data: the packed size if packed, the real size otherwise, padded to 8 bytes.
- Typed ACLs follow in `FS_NAME_ACL` (14) records. `FS_END` (7) ends the backup.

## Testing

```sh
tests/run.sh
```

`tests/sample.backup` is a small archive made on AIX 7.3 with `backup -ipqf` (packed file, hard
link, symlink, FIFO, empty file, nested directories, names with spaces, quotes, backslashes and
UTF-8). `tests/sample.restore-T` is the matching `restore -Tvqf` listing from AIX.

To check a real image, list it on AIX and compare:

```sh
restore -Tvqf host.mksysb > host.T          # on AIX
mksysb2ncdu host.mksysb -o host.json
tests/compare_restore.py host.json host.T
```

Checked against AIX 7.3 TL3 SP1 mksysb images: all 36 519 paths and the total size (2 161 451 722
bytes) match `restore -T`. This includes symlinks, character and block devices, FIFOs, and a 3 GB
file.

## License

MIT, see [LICENSE](LICENSE).
