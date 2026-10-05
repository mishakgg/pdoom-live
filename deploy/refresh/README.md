# Refresh timer skeleton

These unit files are not installed or enabled by `scripts/deploy/release.sh`.

They describe a single-host systemd timer for the bounded refresh command. The service does not import a dataset and does not call `publish-dataset.sh`. Copy them only when an operator chooses to schedule collection, and edit `WorkingDirectory`, `PYTHONPATH`, and `ExecStart` to the checkout path first.

```bash
sudo cp deploy/refresh/pdoom-refresh.service /etc/systemd/system/
sudo cp deploy/refresh/pdoom-refresh.timer /etc/systemd/system/
# Do not run systemctl enable or start as part of a deploy.
```

See `docs/REFRESH.md` for the run-once command, lock recovery, and expected latency while the timer stays disabled.
