#!/usr/bin/env bash
# Pasos que Render ejecuta cada vez que despliega una nueva versión.
set -o errexit   # si un paso falla, el despliegue se detiene

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Datos de ejemplo solo mientras sea un prototipo
if [ "$CARGAR_DEMO" = "1" ]; then
  python manage.py cargar_demo
fi
