#!/bin/sh
set -e

if [ "$1" = 'pytest' ]; then
  exec pytest -q
else
  exec "$@"
fi
