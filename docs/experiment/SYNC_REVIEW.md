# Scoped Sync review: close, timestamps, links and permission expectations

This is a focused source review, not an independent security audit or a device
interoperability result. It accompanies the Sync close regression and corrects a
consumer test assumption. Production path, timestamp, permission and symlink
serialization are unchanged.

## Reviewed references

Kadb baseline: `75678915fd4bdd52345edbb6bc4913ae3415a680`.
AOSP adb source pin: `1cf2f017d312f73b3dc53bda85ef2610e35a80e9`.
The four files were actually downloaded from Gitiles at that commit on
2026-10-26; their byte lengths, URLs and SHA-256 digests are preserved in
[`aosp-source-review.json`](../../validation/sync-close/aosp-source-review.json).
No mutable branch HEAD is used as the reviewed source reference.

- [Sync wire structs](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/file_sync_protocol.h)
- [Daemon receive/send/stat implementation](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/daemon/file_sync_service.cpp)
- [AOSP host Sync implementation](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/client/file_sync_client.cpp)
- [Platform permission-policy hook](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/libs/libadbd_fs/adbd_fs.cpp)

## Close ownership

The fixed `AdbSyncStream.close()` keeps QUIT inside `stream.use`. The stream's
existing close releases its listener in a finally block even if writing CLSE
fails. A failed QUIT therefore no longer bypasses listener removal. The retained
[baseline and focused repair evidence](../../validation/sync-close/README.md)
distinguishes expected defect failures from product-health tests.

## Timestamp representation

Kadb sends `(lastModifiedMs / 1000).toInt()` as the little-endian DONE argument for
both send_v1 and send_v2. AOSP's `sync_data.size` and daemon timestamp variable
are unsigned 32-bit values; send_v2 does not widen this timestamp field. Therefore
sub-second precision is discarded, while values outside unsigned 32-bit epoch
seconds wrap in the existing conversion. The API accepts Long milliseconds and
does not currently validate that wire range. No new range rejection was added
in this compatibility-focused change.

V1 stat/list timestamps are widened from unsigned 32-bit values into Kotlin
Long. V2 stat/list use signed 64-bit seconds, matching their wire structs. A
high-level Path push obtains the timestamp from the canonicalized local target.
A Path pull writes content and does not set local permissions or modification
time; it does not implement the AOSP CLI's optional attribute-restoration path.
These are preserved baseline behaviors, not newly claimed feature support.

## Symbolic links

The high-level local Path push opens file contents and reads mode using stat
behavior: the Darwin/POSIX implementation calls `stat`, and JVM/modern Android
use the default link-following attribute lookup. The last-modified helper
canonicalizes the path. Thus this API follows a local symlink to its contents;
it does not preserve that link as a newly created remote symlink.

For remote metadata, Kadb distinguishes LST2 from STA2. The pinned daemon uses
`lstat` for LST2 and `stat` for STA2. RECV opens the remote path normally and
therefore reads a symlink target. The Native emulator consumer deliberately
creates its test link through shell, then checks lstat, stat and pull-through;
that test must not be described as testing symlink creation via Sync push.

A caller can supply raw Source data and an explicit mode to the lower-level send
API, but Kadb has no dedicated symlink-target encoder. The AOSP host's symlink
branch explicitly reads the link, appends a NUL and sends a single DATA message;
the daemon expects that link-specific format. Generic Source streaming is not a
claim of an equivalent high-level symlink-copy operation. This review does not
change link handling or add target support.

## Requested mode versus effective device mode

The original emulator fixture requested 0600 and incorrectly expected the device
file to retain 0600. The pinned daemon first restricts regular-file mode to 0777
and copies owner bits into group/other bits, so the reviewed pre-policy result is
0666. `handle_send_file` then applies the resulting mode with fchmod. The wire
request remains 0600 in the corrected fixture.

The platform permission hook must also be considered. In the pinned source,
`should_use_fs_config` excludes `/data/` on systems older than Android V; newer
systems can call the hook for this path. The reviewed `adbd_fs_config` applies
only when running as root and when the platform returns an applicable policy.
Different images or vendor policies can therefore change the eventual mode.
The fixture uses a unique regular file under `/data/local/tmp`, records that
actual path, and reports requested 0600, observed mode, reference 0666 and source
URL separately. A mismatch is labeled for policy/wire triage; it is not automatic
proof of a Kadb encoding regression.

The consumer still requires the reference behavior to mark this particular
validation passed. It also compares the mode, size and timestamp with Android's
independent `stat` utility. No chmod is inserted to force an apparent pass, and
no production request bytes are changed. Actual emulator execution is a separate
CI evidence requirement; this source review is not a substitute for it.
