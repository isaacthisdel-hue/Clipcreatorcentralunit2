#!/bin/bash
# Double-click this file to stop ClipCreator.
cd "$(dirname "$0")"
docker compose down
echo "ClipCreator stopped."
read -n 1 -s -r -p "Press any key to close..."
