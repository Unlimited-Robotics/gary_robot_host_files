#!/bin/bash

# Run the command and save the result in a temporary file
result=echo $DISPLAY
temp_file="/tmp/detected_display"
echo $result > $temp_file

# Check if the variable exists in the Bash rc file
bashrc_file="$HOME/.bashrc"
if ! grep -q "export DISPLAY" $bashrc_file; then
    # Add the result to the Bash rc file
    echo "export DISPLAY=$result" >> $bashrc_file
    echo "Added DISPLAY to $bashrc_file"
else
    echo "DISPLAY already exists in $bashrc_file"
fi
