# Third-Party Notices

This repository contains an independent GUI frontend. It does not redistribute
CorridorKey model weights or the CorridorKey runtime. The components below are
either used by the GUI source or included in an optional portable bundle built
on the user's machine.

## tkinterdnd2

- Source: https://github.com/pmgagne/tkinterdnd2
- License: MIT
- Use: native drag-and-drop support for the Tk interface

## Python

- Source: https://www.python.org/
- License: Python Software Foundation License
- Use: the GUI runs on Python; portable bundles include CPython

## Tcl/Tk

- Source: https://www.tcl.tk/
- License: BSD-style Tcl/Tk license
- Use: Tk user interface; portable bundles include Tcl/Tk

## FFmpeg

- Source: https://github.com/FFmpeg/FFmpeg
- License: GPL version 3 or later (the build host's ffmpeg build may enable
  additional codecs; check its build configuration)
- Use: optional portable bundle only; not part of the GUI source
- License text: [packaging/FFMPEG_GPLv3.txt](packaging/FFMPEG_GPLv3.txt)

## Microsoft Visual C++ Redistributable runtime

- Source: the build host's licensed Visual Studio redistribution directory
- Use: optional portable bundle only, copied app-locally; no system-wide
  installation is performed

## CorridorKey 2.0

- Source: https://github.com/nikopueringer/CorridorKey2.0
- License: Corridor Key Licence (a variation of CC BY-NC-SA 4.0 with additional
  terms); see [LICENSE](LICENSE)
- Use: required separately; this repository does not include its code or weights

CorridorKey builds on three foundation models. They are downloaded from their
publishers by the upstream project and are not redistributed here:

- **C-RADIOv4-SO400M** — NVIDIA, NVIDIA Open Model License
  (https://huggingface.co/nvidia/C-RADIOv4-SO400M)
- **MoGe-2 ViT-B** — Microsoft, MIT
  (https://github.com/microsoft/MoGe)
- **RVM (small)** — Google DeepMind, Apache 2.0 code / CC BY 4.0 weights
  (https://github.com/google-deepmind/representations4d)
