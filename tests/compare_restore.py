#!/usr/bin/env python3
"""Compare mksysb2ncdu output with an AIX `restore -Tvqf` listing.

Usage:
  restore -Tvqf x.mksysb > x.T          # on AIX
  mksysb2ncdu x.mksysb -o x.json
  compare_restore.py x.json x.T

Checks that both contain the same set of paths and identical sizes.
Exit status 0 if they match, 1 otherwise.
"""
import json
import re
import sys


def load_restore(path):
    ref = {}
    with open(path, 'rb') as f:
        for line in f:
            m = re.match(rb'\s+(\d+) (\./.*)$', line.rstrip(b'\n'))
            if m:
                ref[m.group(2)[2:]] = int(m.group(1))
    return ref


def load_ncdu(path):
    with open(path, 'rb') as f:
        data = json.loads(f.read().decode('utf-8', 'surrogateescape'))
    out = {}

    def walk(node, prefix):
        if isinstance(node, list):
            info = node[0]
            here = b'' if prefix is None else prefix + info['name'].encode('utf-8', 'surrogateescape') + b'/'
            if prefix is not None and 'mode' in info:
                out[here[:-1]] = info.get('asize', 0)
            for child in node[1:]:
                walk(child, here)
        else:
            out[prefix + node['name'].encode('utf-8', 'surrogateescape')] = node.get('asize', 0)

    walk(data[3], None)
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    mine, ref = load_ncdu(sys.argv[1]), load_restore(sys.argv[2])
    missing = sorted(set(ref) - set(mine))
    extra = sorted(set(mine) - set(ref))
    diff = sorted(k for k in ref if k in mine and ref[k] != mine[k])
    print('paths: restore %d, mksysb2ncdu %d' % (len(ref), len(mine)))
    print('total size: restore %d, mksysb2ncdu %d'
          % (sum(ref.values()), sum(mine[k] for k in ref if k in mine)))
    for label, items in (('missing', missing), ('extra', extra), ('size differs', diff)):
        print('%s: %d' % (label, len(items)))
        for k in items[:10]:
            print('  ' + k.decode('utf-8', 'replace'))
    sys.exit(1 if missing or extra or diff else 0)


if __name__ == '__main__':
    main()
