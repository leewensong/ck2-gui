# Local portable build

This project is an overlay for a CorridorKey 2.0 checkout.  The expected layout is:

```
CorridorKey2.0/
  corridorkey/  infer.py  weights/  vfms/  third_party/
  ck2-gui/      <- this project
```

All commands below run from `CorridorKey2.0\ck2-gui`.  The build script refuses to
run if the sibling CorridorKey checkout is missing.

## 1. Run the GUI tests

```
..\venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 2. Regenerate the icon

The user-maintained icon is `packaging/app.png`. Regenerate all ICO sizes first:

```
..\venv\Scripts\python.exe scripts\prepare_icon.py
```

## 3. Compile the native launcher

Use the Visual Studio x64 tools. In an x64 tools terminal, change into
`packaging` and run:

```
rc /nologo launcher.rc
cl /nologo /utf-8 /O2 /MT /W4 /DWIN32_LEAN_AND_MEAN launcher.c launcher.res /Fe:CorridorKey.exe /link /SUBSYSTEM:WINDOWS /MANIFEST:EMBED /MANIFESTINPUT:launcher.manifest user32.lib
```

## 4. Stage the portable runtime

Run `scripts/build_portable.py` using the CorridorKey venv. It copies a full
CPython with Tcl/Tk, merges the installed dependencies, includes the local
release MSVC CRT, ffmpeg, the models from the sibling CorridorKey checkout, and
the `ck2gui` package. No venv path or `pyvenv.cfg` is copied. Build paths for
Visual Studio/CRT must be adjusted on other build hosts. It refuses to overwrite
an existing staging directory or ZIP.

```
..\venv\Scripts\python.exe scripts\build_portable.py
```

The build host also needs the upstream smoke-test clip at
`..\tmp\smoke_test\input.mp4` (used as `samples/quick-test.mp4`).

## 5. Verify the extracted bundle

From the staging directory, with a PATH containing only Windows/System32:

```
runtime\python.exe -I -B bootstrap.py --check --smoke
```

Then create the CRC-verified ZIP64 archive and SHA-256 checksum:

```
..\venv\Scripts\python.exe scripts\build_portable.py --zip-only
```

Extract to a different location and repeat the runtime and GPU checks there.
Do not publish/upload the bundle automatically. Preserve original licensing,
third-party notices and dependency licenses; confirm upstream redistribution
permissions before sharing or distributing a modified bundle.

`scripts/verify_portable_archive.py` automates the extract-and-verify pass:

```
..\venv\Scripts\python.exe scripts\verify_portable_archive.py dist\CorridorKey2.0-Portable-v1.1.1.zip
```

## 1.1.1 hotfix

The runtime fixes described in `HOTFIX_1.1.1.md` live in the sibling
CorridorKey 2.0 checkout (`corridorkey/runtime.py`, `corridorkey/video_io.py`),
not in this GUI repository. The portable builder copies that checkout, so a
bundle built here includes the fixes. `scripts/stage_hotfix.py` can stage a new
release from an existing 1.1.0 bundle, reusing immutable large assets on the
build host. ZIP members contain real bytes, not hardlinks.

Full native-8K verification and the 4-frame native-8K output check are recorded
in the local CorridorKey checkout's `out_setup/original-8k-fix-verification.json`.
This does not claim that all 861 frames were rendered through stage 2.
