#!/bin/bash

if [ "$#" -eq 0 ]; then
    echo "ERROR: first parameter must be the version to install."
    exit 1
fi

echo

programa1="nombre_programa1"
programa2="nombre_programa2"

if ! command -v wget &> /dev/null || ! command -v curl &> /dev/null; then
    echo "💾 Installing 'wget' and 'curl', type password if asked..."
    echo
    sudo apt-get update && sudo apt-get install -y wget curl
    if [ $? -ne 0 ]; then
        echo
        echo "⚠️  ERROR: Dependencied installation failed, try again."
        exit 1
    fi
fi

ping_url="https://storage.googleapis.com/raya_files/releases/gary_software/ping_file.txt"
gary_url="https://storage.googleapis.com/raya_files/releases/gary_software/$1.tar.gz"

echo 🔗 Checking connection with UR servers...

if ! curl --output /dev/null --silent --head --fail "$ping_url"; then
    echo "⚠️  ERROR: Could not connect with UR servers."
    exit 1
fi

echo 🦿 Checking the requested version...

if ! curl --output /dev/null --silent --head --fail "$gary_url"; then
    echo "⚠️  ERROR: Not valid version $1 ..."
    exit 1
fi

echo 🥫 Downloading docker container image...
echo
docker pull unlimitedrobotics/raya_os_dev.gary_v2.devel:$1
if [ $? -ne 0 ]; then
    echo "⚠️  ERROR: The docker container image download failed, try again."
    exit 1
fi
echo

echo "🤖 Downloading Gary Software version: $1"
echo

cd /home/gary/workspaces/

rm -f $1.tar.gz
wget "$gary_url"
if [ $? -ne 0 ]; then
    rm -f $1.tar.gz
    echo "⚠️  ERROR: The download failed, try again."
    exit 1
fi

echo "🗜  Uncompressing and installing..."
tar -xzf $1.tar.gz
if [ $? -ne 0 ]; then
    rm -f $1.tar.gz
    rm -rf $1
    echo "⚠️  ERROR: The uncompressing and instalation failed, try again."
    exit 1
fi
rm -f $1.tar.gz

echo "🙌 Gary Software $1 successfully installed!"

exit 0
