#!/bin/bash

# --- SOFTWARE TOGGLE FLAG FILE ---
FLAG_PATH="$HOME/.als_controller_state"
# ---------------------------------

# --- ICON PATHS ---
ICON_ENABLED="/usr/share/icons/hicolor/48x48/status/display-brightness.png"
ICON_DISABLED="/usr/share/icons/HighContrast/48x48/status/display-brightness.png"
# ----------------------------------

CURRENT_STATE=1
NEW_STATE=1
NOTIF_MSG="ENABLED"
ICON_PATH="$ICON_ENABLED"

if [ -f "$FLAG_PATH" ]; then
    CURRENT_STATE=$(cat "$FLAG_PATH" 2>/dev/null)
fi

CURRENT_STATE=$(echo "$CURRENT_STATE" | tr -d '\n\r ' | head -c 1)

if [ -z "$CURRENT_STATE" ] || ! [[ "$CURRENT_STATE" =~ ^[01]$ ]]; then
    CURRENT_STATE=1
fi

# Determine the new state (toggle) and set the message/icon
if [ "$CURRENT_STATE" -eq "1" ]; then
    # Current state is 1 (Enabled) -> Set to 0 (Disable)
    NEW_STATE=0
    NOTIF_MSG="DISABLED"
    ICON_PATH="$ICON_DISABLED" # Use the specific DISABLED icon path
else
    # Current state is 0 (Disabled) -> Set to 1 (Enable)
    NEW_STATE=1
    NOTIF_MSG="ENABLED"
    ICON_PATH="$ICON_ENABLED" # Use the specific ENABLED icon path
fi

# Write the new state to the flag file.
echo "$NEW_STATE" > "$FLAG_PATH"

# Send the final confirmation notification, using the specific icon file path (-i flag).
notify-send -t 1500 "Ambient Light Sensor" "$NOTIF_MSG" -i "$ICON_PATH"

exit 0
