#!/bin/bash


LOG_FILE="$HOME/.local/share/iptvselect-fr/logs/cron_curl.log"
OUTPUT_FILE="$HOME/.local/share/iptvselect-fr/info_progs.json"
API_URL="https://www.iptv-select.fr/api/v1/prog"
CONFIG_PY_FILE="/home/$USER/.config/iptvselect-fr/config.py"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

USERNAME=$(pass iptv-select/email)
PASSWORD=$(pass iptv-select/password)

if [[ -z "$USERNAME" || -z "$PASSWORD" ]]; then
    echo "Error: Unable to retrieve credentials from pass." >> "$LOG_FILE"
    exit 1
fi

get_time_from_config() {
    if [[ -f "$CONFIG_PY_FILE" ]]; then
        # Extract the hour and minute values from the Python config file
        CURL_HOUR=$(grep -oP 'CURL_HOUR\s*=\s*\K\d+' "$CONFIG_PY_FILE")
        CURL_MINUTE=$(grep -oP 'CURL_MINUTE\s*=\s*\K\d+' "$CONFIG_PY_FILE")

        # Ensure we have two digits for hour and minute
        CURL_HOUR=$(printf "%02d" $CURL_HOUR)
        CURL_MINUTE=$(printf "%02d" $CURL_MINUTE)
    else
        echo "Error: Unable to retrieve scheduled hour from pass the config file." >> "$LOG_FILE"
        exit 1
    fi
}

get_time_from_config
echo "Script started at $(date). Scheduled time: $CURL_HOUR:$CURL_MINUTE" >> "$LOG_FILE"

LAST_CONFIG_CHECK=$(date +%s)

while true; do
    # Reload config values once per hour to check for changes
    if [ "$(date +%M)" = "00" ]; then
        get_time_from_config
    fi
    # Get current time
    current_hour=$(date +%H)
    current_minute=$(date +%M)

    if [ "$current_hour" = "$CURL_HOUR" ] && [ "$current_minute" = "$CURL_MINUTE" ]; then
        echo "Running scheduled task at $(date)" >> "$LOG_FILE"

        CONFIG_FILE=$(mktemp)
        echo "user = $USERNAME:$PASSWORD" > "$CONFIG_FILE"
        chmod 600 "$CONFIG_FILE"

        curl -H "Accept: application/json;indent=4" --config "$CONFIG_FILE" "$API_URL" > "$OUTPUT_FILE" 2>> "$LOG_FILE"

        rm -f "$CONFIG_FILE"

        echo "Task completed at $(date)" >> "$LOG_FILE"

        # Sleep for 60 seconds to avoid running the task again in the same minute
        sleep 60
    fi

    # Sleep for 30 seconds before checking the time again
    sleep 30
done