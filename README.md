# NLPP #

## Setup ##

- Download and install [Python 3](https://www.python.org/downloads/). Make sure to check the "Add to PATH" option!
- Open up Command Prompt and run `pip install pyyaml`

## Tools ##

- `ie`: `img.bin` unpacker/repacker
- `pe`: Package unpacker/repacker
- `darctool`: DARC unpacker/repacker
- `png2bclim`: `bclim` converter
- `png2texi`: `texi` converter


## Unpacking `img.bin` ##

- Run `./ie unpack` to unpack the contents of `img.bin` into `img_data`


## Unpacking a package ##

- Run `./pe img_data/XXXX unpack`, where `XXXX` is the filename
- The contents will be unpacked into `img_data/XXXX_data`


## Unpacking a DARC ##

- Run `opt/bin/darctool --extract XXXX YYYY`, where `XXXX` is the filename and `YYYY` is the directory to unpack into


## Converting a `bclim` to `png` ##

- Run `opt/bin/png2bclim XXXX` where `XXXX` is the `bclim` file


## Converting a `png` to `bclim` ##

- Run `opt/bin/png2bclim XXXX` where `XXXX` is the `png` file
- NOTE: The converter will save the new file with a name ending in `X.bclim`. Overwrite the original file if the file looks good
- WARNING: Some files currently CAN NOT BE converted. Check that the new `bclim` is the correct size!


## Repacking a DARC ##

- Run `opt/bin/darctool --build XXXX YYYY`, where `XXXX` is the filename and `YYYY` is the directory you unpacked into
- Make sure to delete any temporary files you created in `YYYY`, as `darctool` will repack everything it sees!


## Repacking a package ##

- Run `./pe img_data/XXXX repack`, where `XXXX` is the filename
- The repacked file will be saved as `img_data/new_XXXX` (This is automatically detected by `ie`. There's no need to replace the original `img_data/XXXX` file)
- WARNING: The packer currently CAN NOT repack packages with `smes` files


## Repacking `img.bin` ##

- Run `./ie repack`
- The packer will find any modified files and use them (Ex: `img_data/new_0001`)
