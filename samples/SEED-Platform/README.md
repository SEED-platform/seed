
## SEED Vagrant installation instructions

### Installation
See [Installation Notes](http://www.github.com/seed-platform/seed/wiki/Installation) for setup on Amazon Web Services or a local server.

##### Vagrant installation notes
Both Vagrant and Virtual Box are required

Create a directory for the Virtual Box installation(for instance mkdir SEED-Platform)

Copy the Vagrantfile to /SEED-Platform

###### GitHub notes
##### Local host development is done in the /seed directory UNDER the Vagrant instance(i.e /SEED_Platformt/seed).
#### All changes and commits performed on the host are automatically updated on the Vagrant instance(/vagrant/seed).  

Initialize your working github repository.

Create a working version of the SEED platform from the github repository using the following command 
 
 git clone git@github.com:seed-platform/seed

This will create the /seed directory in the root for your Vagrant installation.

##### Django Database Configuration notes
Edit file local_untracked.py file and configure those settings that are unique for your individual testing.
See the instructions at /seed/LINUX.setup.rst for further instructions as to how to configure. 

###### rename /seed/BE/settings/local_untracked.py to local_untracked.py-backup

###### copy local_untracked.py to /seed/BE/settings/local_untracked.py

##### Javascript Dependencies installation
The installation of the Javascript dependencies to the Vagrant instance requires script install_javascript_dependencies_vagrant.sh
###### copy file install_javascript_dependencies_vagrant.sh to /seed/bin/install_javascript_dependencies_vagrant.sh

##### Vagrant install
Change directory to the Vagrant instance(i.e SEED-Platform)
Create the vagrant instance

   vagrant up —provider=virtualbox

The first time build may take up to 20 minutes.

#####  Accessing SEED from the Vagrant Box
    vagrant ssh
    cd /vagrant
    tmux
    source /vagrant/.virtualenvs/seed/bin/activate
    ./start_celery.sh
    Control-b c (create a new tmux tab)
    cd /vagrant
    source /vagrant/.virtualenvs/seed/bin/activate
    ./start_seed.sh

Clear the browser history if necessary

Browse to http://localhost:8888

Login using the following credentials

    username=seeddevl@lbl.gov  password=demo123

You should now be able to use the SEED Platform
