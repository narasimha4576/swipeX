# Runs the background worker (job imports and cleanup) as its own program.
# Use a terminal where (.venv) is shown.
Set-Location (git rev-parse --show-toplevel)
Set-Location backend
python worker.py