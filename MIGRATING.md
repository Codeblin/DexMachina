# Migrating from DexMachina to PinDroid

DexMachina has been renamed to **PinDroid**.

The maintained package and CLI are now:

```bash
pipx install pindroid
pindroid --help
```

The old `dexmachina` PyPI package receives one final transition release that
depends on `pindroid` and keeps the old `dexmachina` command as a compatibility
wrapper. It prints a deprecation notice on every invocation.

## What changed

| Old | New |
| --- | --- |
| `dexmachina` PyPI package | `pindroid` PyPI package |
| `dexmachina` CLI | `pindroid` CLI |
| `python -m dexmachina` | `python -m pindroid` |
| `dexmachina.toml` | `pindroid.toml` |
| `dexmachina.lock.toml` | `pindroid.lock.toml` |
| `.dexmachina/` workspace | `.pindroid/` workspace |
| `DEXMACHINA_NO_BANNER` | `PINDROID_NO_BANNER` |

## Recommended upgrade

```bash
pipx uninstall dexmachina
pipx install pindroid
pindroid --help
```

For virtual environments:

```bash
python -m pip uninstall dexmachina
python -m pip install pindroid
pindroid --help
```

## PyPI status

After the final `dexmachina` transition release is published, the old PyPI
project should be archived, not deleted. Archiving keeps the name reserved and
visible while signalling that future work has moved to PinDroid.
