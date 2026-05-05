# Stash Deleter — Setup Guide

## Prerequisites

- Python 3.10+
- StashApp running (Docker or native)

---

## 1. Create the virtual environment

Inside the repo root:

```bash
cd /home/smathev/git_dev/stash_deleter
python3 -m venv venv
```

## 2. Install dependencies

```bash
./venv/bin/pip install -r requirements.txt
```

---

## 3. Dev symlink (Docker mount)

StashApp's plugin directory on the dev Docker instance is:

```
/mnt/stashForDevelop/config/plugins/
```

Create a symlink so StashApp sees this repo as an installed plugin:

```bash
ln -s /home/smathev/git_dev/stash_deleter /mnt/stashForDevelop/config/plugins/stash_deleter
```

Verify:

```bash
ls -la /mnt/stashForDevelop/config/plugins/stash_deleter
```

You should see the repo contents (including `stash_deleter.yml`).

---

## 4. Configure the plugin

Copy or edit the sample config:

```bash
# The config lives inside the plugin dir — it's already there after the symlink.
# Edit directly:
$EDITOR /home/smathev/git_dev/stash_deleter/stash_deleter_config.yml
```

Key fields to review before first run:

| Field | Default | Notes |
|---|---|---|
| `dry_run` | `true` | **Leave true until you trust the criteria** |
| `deletion_scope` | `db_only` | `with_file` also deletes the physical file |

---

## 5. Reload plugins in Stash UI

1. Open StashApp in your browser (typically `http://localhost:9999`)
2. Go to **Settings → Plugins**
3. Click **"Reload Plugins"**

The **Dry Run** and **Delete Scenes** tasks will appear under the plugin.

---

## 6. Run tests

```bash
./venv/bin/pytest tests/
```

For verbose output:

```bash
./venv/bin/pytest tests/ -v
```

---

## Troubleshooting

- **Plugin not appearing:** Check the symlink points to the directory containing `stash_deleter.yml`, not a subdirectory.
- **`venv/bin/python3` not found:** Re-run step 1 from the repo root.
- **Permission errors on mount:** Ensure the Docker container has the host path mounted read-write.
