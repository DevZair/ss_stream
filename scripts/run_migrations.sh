#!/bin/bash
set -euo pipefail

python manage.py makemigrations inventory
python manage.py migrate
