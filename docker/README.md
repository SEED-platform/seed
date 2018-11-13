## Run Docker Compose

Resetting the containers can be accomplished by running:
```
docker-compose rm -f
docker volume rm seed_pgdata
docker volume rm seed_media
docker volume create --name=seed_pgdata
docker volume create --name=seed_media
docker-compose up

# Or one line
docker-compose stop && docker-compose rm -f && docker-compose build && docker volume rm seed_pgdata && docker volume create --name=seed_pgdata && docker-compose up

# In another terminal create a user
docker-compose web run ./manage.py create_default_user --username=<email.address> --organization=<org> --password=<password>
```


## Deploying with Docker Stack

Make sure your server has docker installed:

* [Ubuntu](https://docs.docker.com/install/linux/docker-ce/ubuntu/#prerequisites)

Install Docker Compose:

* [Ubuntu](https://docs.docker.com/compose/install/#install-compose)
 
Add user to docker group.

```bash
sudo usermod -a -G docker ubuntu
```


The preferred way to deploy with Docker is using docker swarm and docker stack. 
Look at the deploy.sh script in the root of this repository.

