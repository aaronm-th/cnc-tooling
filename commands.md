Build Docker containers:
docker-compose up -d --build

Open Django container ("django"=name of the container)
docker exec -it django /bin/sh

Open shell
./manage.py shell