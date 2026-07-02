docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build


sudo ssh -L 80:localhost:80 greenuser@100.100.179.127