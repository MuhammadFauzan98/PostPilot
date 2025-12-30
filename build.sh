#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Create instance directory if it doesn't exist
mkdir -p instance

# Run database migrations or initialization if needed
# python init_db.py  # Uncomment if you have a database initialization script
