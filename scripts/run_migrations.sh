#!/bin/bash
set -euo pipefail

python3 manage.py makemigrations inventory
python3 manage.py migrate
