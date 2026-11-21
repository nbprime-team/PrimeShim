# Heap-loaded applications (the shellcode loaders)

The PC profile of the shim can now run the applications that the firmware's own
shellcode loader loads: the launcher allocates a block with the firmware's
`calloc`, copies the image into it, and jumps in with `r0` pointing at the
application folder.  nbCode, primetcc, DOOM and primeLua all work this way, and
none of them could start before the four fixes below.

The symptom on the calculator was "the application exits immediately", which is
a reboot; here it was `[exit] status 2: the editor did not come back cleanly`.

## 1. The heap page had to be executable

The image lives in a block the loader just allocated, so the first instruction
fetch faults on a writable, non-executable page.  `make_heap_page_executable()`
now `mprotect`s it instead of refusing:

```
guest heap page 0x0076d000 is now executable
```

The original objection -- heap SVCs are outside the firmware patch and would
become raw Linux syscalls -- is answered by points 2 and 3.

## 2. The syscall trampoline had to be within `B` range

Firmware SVCs are rewritten to `b <trampoline>`, and the trampoline pool sits
next to the firmware image at 0x30600000.  A heap image at 0x42500000 is 300 MB
away, so `encode_branch` failed and the raw SVC executed:

```
trampoline for SDKLIB___wfopen is outside ARM B range
```

`trampoline_near()` now `mmap`s a 64 KB page within ±30 MB of the faulting SVC
and re-emits the trampoline there.  With this in place the fault-driven patcher
rewrites each heap SVC the first time it runs, and heap code reaches exactly the
handlers the firmware does.

Set `PRIMESHIM_TRACE_HEAP=1` to see each binding:

```
heap SVC 0x01026f -> SDKLIB___wfopen at 0x0076d37c
```

## 3. CP15 cache maintenance traps under QEMU user mode

The loaders run a cache ritual around the input-slot patch (`mcr p15, ...`).
There is no coprocessor to talk to here, so QEMU raises SIGILL on the very
instruction the guest needs to get past.  The SIGILL handler recognises an
`mcr/mrc p15` and skips it -- there is no cache to maintain.

## 4. A stale stream aborted the whole process

```
Fatal error: glibc detected an invalid stdio handle
qemu: uncaught target signal 6 (Aborted)
```

A stream that was not a live `FILE*` reached glibc, and glibc aborts.  The shim
now records every stream it hands out and validates it in
`fread/fwrite/fseek/fclose/filesize`; a stale pointer is logged and returns an
error instead of taking the emulator down.

## Running one headlessly

`tools/run_keys.py` injects device key codes at given times and saves the
framebuffer as a PNG (plus a `.raw`).  The sequence below opens HOME, types
`STARTAPP("nbCode")` and launches it:

```bash
python3 tools/run_keys.py out.png "0xB1@8,0xE047@8.8,0x01@9.2" 36 "21.0,30.0"
```

`0xB1` is Apps, `0xE047` is Home, `0x01` is Esc, `0xB6` is alpha, `0x8B` is
Shift, `0x0D` is Enter, `0x4E` is the `()` key and `0x30` is the `""` key.

Three text-only helpers exist for hosts where images cannot be displayed:

| tool | what it prints |
| --- | --- |
| `tools/fbview.py` | colour histogram and a luminance map of the frame |
| `tools/fbband.py` | a band of the frame, 1:1, as characters |
| `tools/fbdiff.py` | how much of the screen two frames share |

They are what makes "did it draw, and did the keys reach it" answerable without
looking at a picture.
