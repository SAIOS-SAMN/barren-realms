#!/usr/bin/env bash
# launch-galaxy.sh: Spawns authoritative server and 4 autonomous AI captain clients

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Initializing Xylarium Living Galaxy..."

# 1. Start Server Daemon in background
python3 "$SCRIPT_DIR/xylarium-server" &
SERVER_PID=$!
sleep 2

# Trap signals to clean up background child processes on exit
cleanup() {
    echo -e "\nShutting down Xylarium Galaxy..."
    kill $(jobs -p) 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
}
trap cleanup SIGINT SIGTERM EXIT

# 2. Launch Autonomous AI Rival Captains (headless background clients)
python3 "$SCRIPT_DIR/xylarium-client" --ai --personality trader --name "Capt. Vane" --headless &
python3 "$SCRIPT_DIR/xylarium-client" --ai --personality pirate --name "Warlord Malakor" --headless &
python3 "$SCRIPT_DIR/xylarium-client" --ai --personality industrialist --name "Cynthia Voss" --headless &
python3 "$SCRIPT_DIR/xylarium-client" --ai --personality mercenary --name "Ironclaw Rake" --headless &

echo "========================================================================="
echo "Galaxy online! 4 autonomous AI captains roaming the 100 sectors."
echo ""
echo "To join as a human player in another terminal, run:"
echo "   $SCRIPT_DIR/xylarium-client --name 'Captain Solo'"
echo ""
echo "To connect via Telnet door:"
echo "   telnet localhost 2002"
echo "========================================================================="

# Keep script attached to server process
wait $SERVER_PID
