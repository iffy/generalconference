#!/usr/bin/env python
import os
import argparse
import shutil

ap = argparse.ArgumentParser()
ap.add_argument('dirname')
ap.add_argument('-N', '--execute', action='store_true')

args = ap.parse_args()


def merge(what, intowhat, dryrun=True):
    src_files = os.listdir(what)
    for m in src_files:
        src = os.path.join(what, m)
        dst = os.path.join(intowhat, m)
        print 'mv', src, dst
        if not dryrun:
            os.rename(src, dst)
    print 'rm -r', what
    if not dryrun:
        shutil.rmtree(what)

names = {}

for name in os.listdir(args.dirname):
    if '-' not in name:
        continue
    fullpath = os.path.join(args.dirname, name)
    num, slug = name.split('-', 1)
    if slug in names:
        merge(fullpath, names[slug], dryrun=not(args.execute))
    else:
        names[slug] = fullpath