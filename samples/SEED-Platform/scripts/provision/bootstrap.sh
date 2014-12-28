#!/bin/bash
set -e # Exit script immediately on first error.
set -x # Print commands and their arguments as they are executed.

# This script assumes it's run as root.
if [ `whoami` != "root" ]; then
  echo "This install script must be run as root"
  exit 1
fi

# ----------------------------------------------------------------------
# SEED Development Instance
# ----------------------------------------------------------------------
# Bring OS up to date
#apt-get update --fix-missing
#apt-get upgrade -y
apt-get install -y python-software-properties
add-apt-repository ppa:pi-rho/dev

# SEED dependencies
apt-get install -y python-pip python-dev libatlas-base-dev gfortran \
    build-essential g++ make \
    libxml2-dev libxslt1-dev libssl-dev \
    postgresql-9.3 postgresql-server-dev-9.3 libpq-dev \
    libmemcached-dev openjdk-7-jre-headless curl redis-server 
apt-get install python-setuptools

# Development tools
apt-get install -y git-core
apt-get install -y git mercurial python-virtualenv 

# Installing node the easy way - Maybe someday
# https://www.digitalocean.com/community/tutorials/how-to-install-node-js-on-an-ubuntu-14-04-server

# Install Node js
# ---------------
curl -sL https://deb.nodesource.com/setup | sudo bash -

#apt-get update
apt-get install -y nodejs

# Upgrade NPM
# -----------
npm update -g npm

# Install Bower
# -------------
npm install -g bower

# Create PostgreSQL user for seed
# ------------------------------------------------------------
echo 'Postgres setup'
echo '===== Creating PostgreSQL databases and users'
/usr/sbin/update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
sudo su postgres -c "createuser -s -r seeduser"
sudo su - postgres -c "createdb -O seeduser seed_dev"
echo "Creating Role seeduser and Granting Access"
export seedpswd='testing'
sudo su - postgres -c "psql -c \"grant all on database seed_dev to seeduser;\""
sudo su - postgres -c "psql -U postgres -c \"alter user seeduser with password '$seedpswd';\""
echo "Display Postgres Databases, Users and Roles"
sudo su - postgres -c "psql -U postgres --command '\l'"
sudo su - postgres -c "psql -U postgres --command '\du'"
# 
# Edit /etc/postgresql/9.3/main/pg_hba.conf and add the following
# line to the etc/postgresql/9.3/main/pg_hba.conf  area:
chmod 777 /etc/postgresql/9.3/main/pg_hba.conf  
echo 'local   all          seeduser                  md5' >> /etc/postgresql/9.3/main/pg_hba.conf  
#
# local   all        seeduser                       md5
#
# Then restart the postgresql service
#
echo 'Postgres.. Restarting server'
service postgresql restart

#cd /vagrant/seed/BE/settings
#sudo cp local_untracked.py.dist local_untracked.py

# Edit local_untracked.py and edit database and cache settings

#sed -i "s/'seed',/'seed-deploy',/" local_untracked.py
#sed -i "s/'your-username',/'seeduser',/" local_untracked.py
#sed -i "s/'your-password',/'testing',/" local_untracked.py
#sed -i "s/'your-host',/'localhost',/" local_untracked.py
#sed -i "s/'your-port',/'5432',/" local_untracked.py

# Add logging definition, ALLOWED_HOSTS, SERVER_EMAIL, PASSWORD_RESET_EMAIL
#
# Python, Pip, Django install

add-apt-repository ppa:fkrull/deadsnakes
apt-get install -y python2.7-dev python-virtualenv python-setuptools python-pip 

# Upgrade Pip before installing anything with it.
pip install -U pip

# Set up a virtualenv. Make sure to use vagrant's home, otherwise it will be
# created in /root.

if [ ! -d "/vagrant/.virtualenvs" ]; then
	 mkdir /vagrant/.virtualenvs
	 virtualenv -p python2.7 /vagrant/.virtualenvs/seed
else
	rm -r /vagrant/.virtualenvs
 	mkdir /vagrant/.virtualenvs
	virtualenv -p python2.7 /vagrant/.virtualenvs/seed
fi

echo "Activating seed environment"
source /vagrant/.virtualenvs/seed/bin/activate

# Install the requirements. Without the `--pre` flag Pip would see pytz's
# releases as pre-release versions and fail.
echo "Installing Django project Requirements"
pip install --upgrade --pre --requirement /seed/requirements.txt
pip freeze

echo "Installing Node,Npm and Javascript Dependencies"
cd /vagrant/seed/bin
echo "Running node-and-npm-in-30s.sh"
./node-and-npm-in-30s.sh
echo "Installing javascript dependencies and fineuploader"
npm install grunt --save-dev
npm install -g grunt-cli

cd /vagrant/seed/bin
./install_javascript_dependencies_vagrant.sh

cd /vagrant/seed

echo "Django settings....clear run syncdb, migrate and create user seeddev"

export DJANGO_SETTINGS_MODULE=BE.settings.dev
export ONLY_HTTPS=False
./manage.py syncdb
./manage.py migrate
./manage.py create_default_user --username=seeddev@lbl.gov --organization=lbl --password=demo123
echo "Finished"
