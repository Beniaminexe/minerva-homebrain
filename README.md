# Minerva – Homelab Brain

Minerva is a self-hosted "home brain" that runs in your homelab and coordinates:

- ✅ Reminders (pills, workouts, routines)
- ✅ Service monitoring (Cartofia, Minecraft server, etc.)
- ✅ An ESP32 / NerdMiner display as a tiny status dashboard
- ✅ A chatty LLM assistant
- 🔜 Telegram bot & Web UI
- 🔜 Proxmox integration and GPU-accelerated local models

## Stack

- **Backend:** Python, FastAPI
- **Runtime:** Proxmox LXC/VM in the homelab
- **LLM:** Local (Ollama / llama.cpp) or external API (TBD)
- **Frontend:** ESP32 TFT display, Web UI (later), Telegram (later)

## Getting Started (Dev)

```bash
git clone git@github.com:Beniaminexe/minerva-homebrain.git
cd minerva-homebrain

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

./run_dev.sh
