# Runset builder

A self-contained HTML page for authoring `*.runset.json` files for the
imgSequel pipeline. No backend, no build step, no install.

## Open it

Easiest — just open the file directly in any modern browser:

```bash
open webui/index.html      # macOS
xdg-open webui/index.html  # Linux
```

Or serve it from the project root (handy if your browser is fussy about
`file://` paths):

```bash
python3 -m http.server 8000
# then visit http://localhost:8000/webui/
```

## Use it

1. The form is pre-filled with the built-in defaults — the same 5 questions
   and 12 variants as `qwen_critique_loop/runset.py::RunConfig.default()`.
2. Edit anything: rename variants, change strengths/steps/seeds, rewrite
   questions, add or remove rows.
3. The **JSON preview** at the bottom updates live and shows exactly what
   will be saved.
4. Set the output filename (defaults to `myrun.runset.json`) and click
   **download runset.json**.

To pick up where you left off later, click **load runset…** and select a
previously-saved JSON file. The form repopulates so you can keep iterating.

## Run with it

Once you have a runset file (locally, or after `scp` to the miniPC):

```bash
# fresh run with your custom runset
bash scripts/launch.sh myfile.pdf --pages 1-3 --runset myrun.runset.json

# resume an in-progress run (uses the runset saved with that run)
bash scripts/launch.sh --resume latest
```

The runset is copied into the run directory as `runset.json` and also
embedded in `run.json`, so every run is fully self-describing.

## Schema

`*.runset.json` files are versioned. The current schema is `version: 1`,
defined in `qwen_critique_loop/runset.py`. If you bump the schema in
Python, also bump the `DEFAULTS.version` block at the top of
`webui/index.html` and any backwards-compat handling in `RunConfig.from_dict`.
