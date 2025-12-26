#!/bin/bash
clear
docker rm -f $(docker ps -aq)
clear
docker compose up -d --build
docker compose exec -it backend python manage.py makemigrations
docker compose exec -it backend python manage.py migrate
clear
docker compose exec -it backend python manage.py createsuperuser
