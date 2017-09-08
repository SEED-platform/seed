## Run Docker Compose

Resetting the containers can be accomplished by running:
```
docker-compose rm -f
docker volume rm seed_pgdata
docker volume create --name=seed_pgdata
docker volume create --name=seed_media
docker-compose up

# Or one line
docker-compose stop && docker-compose rm -f && docker-compose build && docker volume rm seed_pgdata && docker volume create --name=seed_pgdata && docker-compose up

# In another terminal create a user
docker-compose web run ./manage.py create_default_user --username=<email.address> --organization=<org> --password=<password>
```

