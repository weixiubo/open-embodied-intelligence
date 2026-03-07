# OpenEI Dance Demo

This example is the reference Phase 1 application built on top of OpenEI.

It demonstrates:

- profile-driven runtime setup
- deterministic vs. llm-assisted brain selection
- simulation and legacy transport switching
- scripted, text, and live-speech input modes

Example commands:

```bash
python examples/dance_demo/run.py --profile demo --transport sim
python examples/dance_demo/run.py --profile demo --transport sim --text "dance 50 seconds" --text "confirm" --once
python examples/dance_demo/run.py --profile demo --transport sim --text "announce OpenEI is ready" --once
python examples/dance_demo/run.py --profile dev --brain llm-assisted --transport sim
```

Notes:

- use English example commands in repository docs to avoid Windows GBK terminal corruption
- the deterministic brain still supports the existing Chinese speech command set at runtime
