rm /home/holger/.config/keyhint/*
cd /home/holger/coding/keyhint/
.venv/bin/python -m keyhint 2>&1 | tee run.log
