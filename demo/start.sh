#!/bin/bash
# Main control script for demo: interactive menu to manage parts
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$DEMO_DIR/venv"
PYTHON="$VENV_DIR/bin/python3"
PARTS_DIR="$DEMO_DIR/parts"
LOGS_DIR="$DEMO_DIR/logs"

# Ensure venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "[ERROR] Virtual environment not found. Run: ./setup.sh"
    exit 1
fi

# Function to show menu
show_menu() {
    echo ""
    echo "========================================"
    echo "  IoT Foundry PLDM Demo Control Panel"
    echo "========================================"
    
    # Check running status
    local server_status="[STOPPED]"
    local agent_status="[STOPPED]"
    local config_status="[READY]"
    
    if [ -f "$LOGS_DIR/redfish_server.log" ]; then
        if grep -q "Server listening" "$LOGS_DIR/redfish_server.log" 2>/dev/null; then
            server_status="[RUNNING]"
        fi
    fi
    
    echo ""
    echo "Current Status:"
    echo "  Redfish Server:  $server_status"
    echo "  Runtime Agent:   $agent_status"
    echo "  Configurator:    $config_status"
    echo ""
    echo "Available Commands:"
    echo "  1) Start Redfish Mockup Server"
    echo "  2) Run Configurator (scan → generate mockup)"
    echo "  3) Start Runtime Agent"
    echo "  4) View Logs (select which)"
    echo "  5) Stop All Running Parts"
    echo "  6) Show Status"
    echo "  0) Exit"
    echo ""
}

# Function to start server
start_server() {
    echo "[INFO] Starting Redfish Mockup Server..."
    nohup "$PYTHON" "$PARTS_DIR/redfish_server.py" >> "$LOGS_DIR/redfish_server.log" 2>&1 &
    local pid=$!
    echo "[OK] Redfish Server started (PID: $pid)"
    echo "$pid" > "$LOGS_DIR/redfish_server.pid"
    sleep 2
    tail -n 20 "$LOGS_DIR/redfish_server.log"
}

# Function to run configurator
run_configurator() {
    echo "[INFO] Running Configurator..."
    "$PYTHON" "$PARTS_DIR/configurator.py"
    echo "[OK] Configurator finished"
}

# Function to start agent
start_agent() {
    echo "[INFO] Starting Runtime Agent..."
    nohup "$PYTHON" "$PARTS_DIR/runtime_agent.py" >> "$LOGS_DIR/runtime_agent.log" 2>&1 &
    local pid=$!
    echo "[OK] Runtime Agent started (PID: $pid)"
    echo "$pid" > "$LOGS_DIR/runtime_agent.pid"
    sleep 2
    tail -n 20 "$LOGS_DIR/runtime_agent.log"
}

# Function to view logs
view_logs() {
    echo "Select log to view:"
    echo "  1) Redfish Server"
    echo "  2) Configurator"
    echo "  3) Runtime Agent"
    echo "  0) Back"
    read -p "Choice: " choice
    
    case "$choice" in
        1) tail -f "$LOGS_DIR/redfish_server.log" ;;
        2) tail -f "$LOGS_DIR/configurator.log" ;;
        3) tail -f "$LOGS_DIR/runtime_agent.log" ;;
        0) return ;;
        *) echo "[ERROR] Invalid choice" ;;
    esac
}

# Function to stop all
stop_all() {
    echo "[INFO] Stopping all parts..."
    
    for pidfile in "$LOGS_DIR"/*.pid; do
        if [ -f "$pidfile" ]; then
            local pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                echo "[INFO] Stopping process $pid..."
                kill -TERM "$pid" 2>/dev/null || true
            fi
        fi
    done
    
    sleep 1
    echo "[OK] All parts stopped"
}

# Function to show status
show_status() {
    echo ""
    echo "System Status:"
    echo "  Demo Root: $DEMO_DIR"
    echo "  Venv: $VENV_DIR"
    echo "  Logs: $LOGS_DIR"
    echo ""
    
    for logfile in "$LOGS_DIR"/*.log; do
        if [ -f "$logfile" ]; then
            local name=$(basename "$logfile" .log)
            echo "  $name:"
            tail -n 3 "$logfile" | sed 's/^/    /'
        fi
    done
}

# Main loop
mkdir -p "$LOGS_DIR"

while true; do
    show_menu
    read -p "Enter choice [0-6]: " choice
    
    case "$choice" in
        1) start_server ;;
        2) run_configurator ;;
        3) start_agent ;;
        4) view_logs ;;
        5) stop_all ;;
        6) show_status ;;
        0) 
            echo "[INFO] Exiting..."
            stop_all
            exit 0
            ;;
        *)
            echo "[ERROR] Invalid choice. Please try again."
            ;;
    esac
    
    read -p "Press Enter to continue..."
done
