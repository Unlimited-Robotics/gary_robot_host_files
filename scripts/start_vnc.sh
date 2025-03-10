#!/bin/bash

# Run the command and store the output in a variable
display_output=$(ps e -u $USER | grep -Po "DISPLAY=:[\.0-9A-Za-z:]* " | sort -u)

if [ -z "$display_output" ]; then
    echo "Error: Unable to retrieve display information."
    exit 1
fi

# Extract the first display from the output
first_display=$(echo "$display_output" | head -n 1)

# Extract the value of the display (e.g., ":0") from the string
export_display=$(echo "$first_display" | grep -Po "(?<=DISPLAY=)[\.0-9A-Za-z:]*")

# Export the display as an environment variable
export DISPLAY="$export_display"

# Optional: Print the exported display for verification
echo "Exported DISPLAY '$DISPLAY'"

pkill vino
/usr/lib/vino/vino-server --display=$DISPLAY