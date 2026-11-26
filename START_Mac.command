#!/bin/bash
# Doppelklick startet die Weboberfläche (braucht Python 3.10+)
cd "$(dirname "$0")"
python3 start.py "$@"
