#!/bin/bash
# WVU LCSEE VPN toggle script (openconnect / GlobalProtect)
# Usage: wvu-vpn.sh [connect|disconnect|toggle|status]
#
# Credentials via env vars (preferred) or interactive prompt:
#   VPN_USER=cwc00024 VPN_PASS=yourpass wvu-vpn.sh connect

CONF="/home/connor/AI-Tools/scripts/wvu-vpn.conf"
LOG="/tmp/wvu-vpn.log"

# Log all output for debugging (viewable with: tail -f /tmp/wvu-vpn.log)
exec >> "$LOG" 2>&1
echo "--- $(date) --- $0 $*"

is_connected() {
    pgrep -x openconnect > /dev/null 2>&1
}

get_credentials() {
    VPN_USER="${VPN_USER:-}"
    VPN_PASS="${VPN_PASS:-}"

    # Use zenity GUI dialogs when running without a terminal (e.g. GNOME button)
    if [[ -z "$VPN_USER" ]]; then
        if ! [ -t 0 ] && [[ -n "$DISPLAY" ]]; then
            VPN_USER=$(zenity --entry --title="WVU VPN" --text="Username:" --entry-text="cwc00024" 2>/dev/null)
        else
            read -rp "VPN username: " VPN_USER
        fi
    fi
    if [[ -z "$VPN_PASS" ]]; then
        if ! [ -t 0 ] && [[ -n "$DISPLAY" ]]; then
            VPN_PASS=$(zenity --password --title="WVU VPN" --text="Password for $VPN_USER:" 2>/dev/null)
        else
            read -rsp "VPN password: " VPN_PASS
            printf "\n"
        fi
    fi

    if [[ -z "$VPN_USER" || -z "$VPN_PASS" ]]; then
        echo "Credentials empty, aborting"
        exit 1
    fi
}

do_connect() {
    if is_connected; then
        notify-send -i network-vpn "WVU VPN" "Already connected" 2>/dev/null
        echo "Already connected"
        return 0
    fi

    get_credentials

    notify-send -i network-vpn "WVU VPN" "Connecting..." 2>/dev/null
    echo "Running openconnect..."

    echo "$VPN_PASS" | sudo openconnect \
        --config="$CONF" \
        --user="$VPN_USER" \
        --passwd-on-stdin \
        --background \
        --script=/usr/share/vpnc-scripts/vpnc-script \
        2>&1

    echo "openconnect exited with code $?"

    # Poll up to 20s for openconnect process to appear
    local connected=false
    for _ in $(seq 1 20); do
        sleep 1
        if is_connected; then
            connected=true
            break
        fi
    done

    if $connected; then
        notify-send -i network-vpn "WVU VPN" "Connected" 2>/dev/null
        echo "Connected (PID: $(pgrep -x openconnect))"
    else
        notify-send -i dialog-error "WVU VPN" "Connection failed — check /tmp/wvu-vpn.log" 2>/dev/null
        echo "Connection failed"
        return 1
    fi
}

do_disconnect() {
    if ! is_connected; then
        notify-send -i network-vpn "WVU VPN" "Not connected" 2>/dev/null
        echo "Not connected"
        return 0
    fi

    sudo pkill -SIGTERM openconnect
    sleep 1

    notify-send -i network-vpn "WVU VPN" "Disconnected" 2>/dev/null
    echo "Disconnected"
}

do_status() {
    if is_connected; then
        echo "connected (PID: $(pgrep -x openconnect))"
    else
        echo "disconnected"
    fi
}

case "${1:-toggle}" in
    connect)    do_connect ;;
    disconnect) do_disconnect ;;
    toggle)
        if is_connected; then
            do_disconnect
        else
            do_connect
        fi
        ;;
    status) do_status ;;
    *)
        echo "Usage: $0 {connect|disconnect|toggle|status}"
        exit 1
        ;;
esac
