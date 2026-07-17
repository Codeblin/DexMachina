# DexMachina has been renamed to PinDroid

> **Deprecated package:** `dexmachina` is now **PinDroid**.
>
> Install the maintained package instead:
>
> ```bash
> pip install pindroid
> # or, recommended for CLI use:
> pipx install pindroid
> ```

This final `dexmachina` release exists only as a transition bridge. It depends
on `pindroid` and keeps the old `dexmachina` console command as a thin wrapper
so existing scripts do not fail immediately.

New projects should use:

```bash
pindroid --help
pindroid up --profile dynamic
```

The old `dexmachina` package is inactive and will be archived on PyPI after
this transition release. Do not start new automation against the old package
name.

Migration:

```bash
pip uninstall dexmachina
pip install pindroid
```

If you use `pipx`:

```bash
pipx uninstall dexmachina
pipx install pindroid
```

Project home: <https://github.com/Codeblin/PinDroid>
