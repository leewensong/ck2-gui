# Notice

`ck2-gui` is an **independent, unofficial local desktop frontend** for
[CorridorKey 2.0](https://github.com/nikopueringer/CorridorKey2.0). It is not
affiliated with, endorsed by, or sponsored by Corridor Digital, and it is not
the official CorridorKey plugin.

## What this repository contains

- Original GUI/frontend code (`ck2gui/`), launcher/build scripts, tests, and
  documentation.
- No CorridorKey model weights, no CorridorKey runtime source, and no
  third-party foundation model weights. Users must obtain CorridorKey 2.0 and
  its weights separately from the upstream project.

## Licensing

The original code in this repository is made available under the same terms as
the CorridorKey 2.0 license (see [LICENSE](LICENSE)), to the extent it is a
derivative or companion work. The CorridorKey name is retained as required by
that license. Third-party components retain their own licenses; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Upstream project

CorridorKey 2.0 was designed and trained by Zachary Harris in collaboration
with Niko and Corridor Digital.

- Upstream repository: https://github.com/nikopueringer/CorridorKey2.0
- Official plugin and standalone app: https://corridorkey.com

## Portable bundles

`scripts/build_portable.py` can assemble a local portable bundle from a
CorridorKey 2.0 checkout. Such a bundle contains upstream code, model weights,
Python, ffmpeg, and other third-party components. It is a separate artifact:
review the upstream license and all third-party terms before sharing,
repackaging, or using it commercially. The bundle is not published with this
repository.
