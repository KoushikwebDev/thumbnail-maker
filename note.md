python -m venv .venv
source .venv/bin/activate

pip install requests

select interpreter => choose workspace

uv init
uv add requests
uv run main.py