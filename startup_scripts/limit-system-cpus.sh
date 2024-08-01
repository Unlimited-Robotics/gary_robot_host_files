#!/bin/bash

ENV_FILE="/opt/raya_os/env"

# Read general env file
if [ -f ${ENV_FILE} ]; then
    source ${ENV_FILE}
else
    echo "File '${ENV_FILE}' not found, ignoring it."
fi

if [ -z "${DEFAULT_CPUS+x}" ]; then
    NUM_CPUS=$(grep -c ^processor /proc/cpuinfo)
    export DEFAULT_CPUS="$((NUM_CPUS - 2)),$((NUM_CPUS - 1))"
fi

echo "Setting system cores as: ${DEFAULT_CPUS}"

cd /sys/fs/cgroup/cpuset
mkdir -p sys
echo ${DEFAULT_CPUS} > sys/cpuset.cpus
echo 0 > sys/cpuset.mems
echo 0 > sys/cpuset.cpu_exclusive

date > /tmp/last_cpu_limit_date.txt
cat tasks | wc -l > /tmp/num_processes_before_cpu_limit.txt
for T in `cat tasks`; do /bin/echo $T > sys/tasks 2>/dev/null; done; true
cat tasks | wc -l > /tmp/num_processes_after_cpu_limit.txt
