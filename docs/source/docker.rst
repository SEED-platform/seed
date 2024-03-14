========================
Docker Deployment on AWS
========================

Amazon Web Services (`AWS`_) provides the preferred hosting for the SEED Platform.

**seed** is a `Django Project`_ and Django's documentation is an excellent place for general
understanding of this project's layout.

.. _Django Project: https://www.djangoproject.com/

.. _AWS: http://aws.amazon.com/

Installation
^^^^^^^^^^^^

Ubuntu server 18.04 or newer with a m5ad.xlarge (if using in Production instance)

* After launching the instance, run the following commands to install docker.

.. code-block:: console

    # Install any upgrades
    sudo apt-get update
    sudo apt-get upgrade -y

    # Remove any old docker engines
    sudo apt-get remove docker docker-engine docker.io containerd runc

    # Install docker community edition
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository \
        "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) \
        stable"

    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    # Add your user to the docker group
    sudo groupadd docker
    sudo usermod -aG docker $USER
    newgrp docker

.. note:: It is okay if the first command fails

* Verify that the DNS is working correctly. Run the following and verify the response lists IPs (v6 most likely)

.. code-block:: console

    # verify that the dns resolves
    docker run --rm seedplatform/seed getent hosts seed-platform.org
    # or
    docker run --rm tutum/dnsutils nslookup email.us-west-2.amazonaws.com

* Install Docker compose

.. code-block:: console

    sudo curl -L "https://github.com/docker/compose/releases/download/1.25.4/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose

* Checkout SEED (or install from the releases).

.. code-block:: console

    git clone

* Add in the Server setting into profile.d. For example add the content below (appropriately filled out) into /etc/profile.d/seed.sh

.. code-block:: console

    export POSTGRES_USER=seed
    export POSTGRES_DB=seed
    export POSTGRES_PASSWORD=GDEus3fasd1askj89QkAldjfX
    export POSTGRES_PORT=5432
    export SECRET_KEY="96=7jg%_&1-z9c9qwwu2@w$hb3r322yf3lz@*ekw-1@ly-%+^"

    # The admin user is only valid only until the database is restored
    export SEED_ADMIN_USER=user@seed-platform.org
    export SEED_ADMIN_PASSWORD="7FeBWal38*&k3jlfa92lakj8ih4"
    export SEED_ADMIN_ORG=default

    # For SES
    export AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY>
    export AWS_SECRET_ACCESS_KEY=<AWS_SECRET_KEY>
    export AWS_SES_REGION_NAME=us-west-2
    export AWS_SES_REGION_ENDPOINT=email.us-west-2.amazonaws.com
    export SERVER_EMAIL=user@seed-platform.org


* Before launching the first time, make sure the persistent volumes and the backup directory exist.

.. code-block:: console

    docker volume create --name=seed_pgdata
    docker volume create --name=seed_media

    mkdir -p $HOME/seed-backups

.. note:: Make sure to have the seed-backups in your path, otherwise the db-postgres container will not launch.

* Launch the project

.. code-block:: console

    cd <checkout dir>
    ./deploy.sh


Deploying with Docker
^^^^^^^^^^^^^^^^^^^^^

The preferred way to deploy with Docker is using docker swarm and docker stack.
Look at the `deploy.sh script`_  for implementation details.

The short version is to simply run the command below. Note that the passing of the docker-compose.yml filename is not required if using docker-compose.local.yml.

```bash
./deploy.sh docker-compose.local.yml
```

If deploying using a custom docker-compose yml file, then simple replace the name in the command above.


.. _`deploy.sh script`: https://github.com/SEED-platform/seed/blob/develop/deploy.sh
.. _`JSON Type`: https://www.postgresql.org/docs/9.4/datatype-json.html
