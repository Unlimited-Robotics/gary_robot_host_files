#!/bin/bash

cd /sys/fs/cgroup/cpuset
mkdir -p sys
echo 10,11 > sys/cpuset.cpus
echo 0 > sys/cpuset.mems
echo 0 > sys/cpuset.cpu_exclusive

date > /tmp/last_cpu_limit_date.txt
cat tasks | wc -l > /tmp/num_processes_before_cpu_limit.txt
for T in `cat tasks`; do echo "Moving " $T; /bin/echo $T > sys/tasks; done; true
cat tasks | wc -l > /tmp/num_processes_after_cpu_limit.txt
