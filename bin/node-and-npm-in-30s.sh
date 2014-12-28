# The install script
# Adapted from https://gist.github.com/579814
# https://gist.github.com/dwayne/2983873
 
echo '# Added by install script for node.js and npm in 30s' >> ~/.bashrc
echo 'export PATH=$HOME/local/bin:$PATH' >> ~/.bashrc
echo 'export NODE_PATH=$HOME/local/lib/node_modules' >> ~/.bashrc
. ~/.bashrc
 
mkdir -p ~/local
mkdir -p ~/Downloads/node-latest-install
 
cd ~/Downloads/node-latest-install
curl http://nodejs.org/dist/v0.10.28/node-v0.10.28.tar.gz | tar xz --strip-components=1
 
./configure --prefix=~/local # if SSL support is not required, use --without-ssl
make install # ok, fine, this step probably takes more than 30 seconds...
