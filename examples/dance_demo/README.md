# OpenEI Dance Demo

This example runs the legacy dance capability on top of the OpenEI runtime.
It now also exercises a non-motion skill so the example is no longer dance-only.

## Interactive text mode

```bash
openei run --profile demo --transport sim --input-mode text
```

## One-shot scripted mode

```bash
openei run --profile demo --transport sim --text "跳舞十秒" --once
openei run --profile demo --transport sim --text "播报OpenEI准备好了" --once
```

## Inspect runtime

```bash
openei inspect --profile demo --transport sim --format json
```
