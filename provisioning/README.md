# Provisioning with Ansible

For those who are trying to automate the setup of SEED plataform I've written a playbook to setup the infrastructure and application within AWS.

The playbook will create a RDS instance, one Elasticache node with Redis and a single instance that will run SEED application.

I don't know if everybody has knowledge about ansible, but it is a attempt to facilitate the provisioning stuff.

The configuration is separated in two steps. The first one will take care about the AWS services, and the second one will install all necessary dependencies and software. At the end of the playbook you will get a running instance with Nginx doing a proxy to the SEED application.

The main configurations that you need to change are inside the file vars/seed.yml, there you can find the a lot of variables that you need to adequate to your environment. All the important variables are between ##.

