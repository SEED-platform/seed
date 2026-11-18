========================
Docker Deployment on AWS
========================

Amazon Web Services (`AWS`_) provides the preferred hosting for the SEED Platform.

**seed** is a `Django Project`_ and Django's documentation is an excellent place for general
understanding of this project's layout.

.. _Django Project: https://www.djangoproject.com/

.. _AWS: https://aws.amazon.com/

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

* Add the server settings that ``docker-compose.yml`` passes through to the containers into profile.d. For example
  add the content below (appropriately filled out) into /etc/profile.d/seed.sh

.. code-block:: console

    # For SES
    export AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY>
    export AWS_SECRET_ACCESS_KEY=<AWS_SECRET_KEY>
    export AWS_SES_REGION_NAME=us-west-2
    export AWS_SES_REGION_ENDPOINT=email.us-west-2.amazonaws.com
    export SERVER_EMAIL=user@seed-platform.org

    # For custom cookie validity duration
    export COOKIE_EXPIRATION=1209600


* Before launching the first time, make sure the persistent volumes exist.

.. code-block:: console

    docker volume create --name=seed_pgdata
    docker volume create --name=seed_media

* ``docker-compose.yml`` contains example values for the database password, ``SECRET_KEY``, and the SEED admin
  user. Replace them in a ``docker-compose.override.yml`` next to it, which Docker Compose loads automatically and
  git ignores. The admin user is only created if it does not already exist.

.. code-block:: yaml

    services:
      db-postgres:
        environment:
          - POSTGRES_PASSWORD=<database password>
      web:
        environment:
          - POSTGRES_PASSWORD=<database password>
          - SECRET_KEY=<secret key>
          - SEED_ADMIN_USER=<admin email>
          - SEED_ADMIN_PASSWORD=<admin password>
          - SEED_ADMIN_ORG=<organization>
      web-celery:
        environment:
          - POSTGRES_PASSWORD=<database password>
          - SECRET_KEY=<secret key>

* Launch the project

.. code-block:: console

    cd <checkout dir>
    docker compose up -d


.. _`JSON Type`: https://www.postgresql.org/docs/9.4/datatype-json.html
