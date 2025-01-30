#!/bin/bash

SOURCE_DIR="/opt/ur/services"
DEST_DIR="/etc/systemd/system"

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Directory $SOURCE_DIR does not exist."
    exit 1
fi

for service_file in "$SOURCE_DIR"/*.service; do
    if [[ -f "$service_file" ]]; then
        service_name=$(basename "$service_file")
        dest_link="$DEST_DIR/$service_name"

        if [[ -e "$dest_link" ]]; then
            echo "File $dest_link exist, deleting."
            rm $dest_link
        fi
        cp "$service_file" "$dest_link"
        echo "Copy service: $service_file -> $dest_link"
        systemctl enable "$service_name"
        systemctl start "$service_name"
        echo "Service enabled: $service_name"
    fi

done
