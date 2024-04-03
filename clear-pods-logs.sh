#!/bin/bash
namespace="dev"

# Get the list of pods in the namespace
pods=$(kubectl get pods -n $namespace --no-headers=true | awk '{print $1}' | grep 'abc-pod\|def-pod\|ghi-pod')

# Iterate over the list of pods and log into each pod
for pod in $pods; do
  if [[ $pod == *"abc"*]]; then
  echo "abc pod found: $pod"
  kubectl -n $namespace exec -it $pod -c abc -- /bin/bash -c rm -rf /mnt/logs/
  kubectl -n $namespace delete pod $pod --grace-period 0 --force
  fi 
  if [[ $pod == *"def"*]]; then
  echo "def pod found: $pod"
  kubectl -n $namespace exec -it $pod -c abc -- /bin/bash -c rm -rf /mnt/logs/
  kubectl -n $namespace delete pod $pod --grace-period 0 --force
  fi 
  if [[ $pod == *"ghi"*]]; then
  echo "abc pod found: $pod"
  kubectl -n $namespace exec -it $pod -c abc -- /bin/bash -c rm -rf /mnt/logs/
  kubectl -n $namespace delete pod $pod --grace-period 0 --force
  fi 
done
