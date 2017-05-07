#!/usr/bin/python
from img import Image, FileWindow
import os

img = Image('new_img.bin')

filenames = os.listdir('img')
filenames.sort()

print '[+] Packing all resources'

for fn in filenames:
    idx = int(fn, 16)
    while len(img.entries) < idx:
        img.entries.append(None)

    fn = 'img/%s' % fn
    sz = os.stat(fn).st_size
    img.entries.append(FileWindow(fn, 0, sz))

img.write()

print '[+] Done!'
