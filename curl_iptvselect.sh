#!/bin/bash

SERVICE="iptv-select"
PYTHON="$HOME/.local/share/iptvselect-fr/.venv/bin/python"

CRYPTED_CREDENTIALS=$($PYTHON -c "import sys; sys.path.insert(0, '$HOME/.config/iptvselect-fr'); import config; print(config.CRYPTED_CREDENTIALS)")

LOG_FILE="$HOME/.local/share/iptvselect-fr/logs/cron_curl.log"
OUTPUT_FILE="$HOME/.local/share/iptvselect-fr/info_progs.json"
API_URL="https://www.iptv-select.fr/api/v1/prog"

if [[ "$CRYPTED_CREDENTIALS" == "True" ]]; then
    USERNAME=$($PYTHON -c "import keyring; print(keyring.get_password('$SERVICE', 'username'))")
    PASSWORD=$($PYTHON -c "import keyring; print(keyring.get_password('$SERVICE', 'password'))")

    if [[ -z "$USERNAME" || -z "$PASSWORD" ]]; then
        echo "Error: Unable to retrieve credentials from keyring." >> "$LOG_FILE"
        exit 1
    fi

    CONFIG_FILE=$(mktemp)
    echo "user = $USERNAME:$PASSWORD" > "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"

    curl -H "Accept: application/json;indent=4" --config "$CONFIG_FILE" "$API_URL" > "$OUTPUT_FILE" 2>> "$LOG_FILE"

    rm -f "$CONFIG_FILE"

    unset USERNAME PASSWORD
else
    curl -H "Accept: application/json;indent=4" -n "$API_URL" > "$OUTPUT_FILE" 2>> "$LOG_FILE"
fi
