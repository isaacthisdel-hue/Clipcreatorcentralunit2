#!/bin/bash
# Double-click this file to start ClipCreator.
cd "$(dirname "$0")"

if grep -q "^ANTHROPIC_API_KEY=PASTE_YOUR_CLAUDE_KEY_HERE" .env; then
  echo ""
  echo "STOP: you haven't added your Claude API key yet."
  echo "Open the file named .env in this folder (press Cmd+Shift+. in Finder to see it),"
  echo "replace PASTE_YOUR_CLAUDE_KEY_HERE with your key, save, then double-click this again."
  echo ""
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

if ! docker info > /dev/null 2>&1; then
  echo ""
  echo "STOP: Docker Desktop isn't running. Open Docker Desktop, wait for the whale icon to stop moving, then try again."
  echo ""
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

echo "Starting ClipCreator. The FIRST time takes 10-20 minutes (it's building everything). After that, ~1 minute."
docker compose up -d --build || { echo "Something failed. Copy the text above and send it to Claude."; read -n 1 -s -r; exit 1; }

echo "Waiting for the app to come up..."
for i in $(seq 1 90); do
  if curl -s -o /dev/null http://localhost:3107; then break; fi
  sleep 5
done
open http://localhost:3107
echo ""
echo "ClipCreator is running at http://localhost:3107"
echo "To stop it later: double-click 'Stop ClipCreator.command'."
read -n 1 -s -r -p "Press any key to close this window (the app keeps running)..."
