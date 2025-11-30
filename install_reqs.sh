# Build tools and Pi 3.13
cd /tmp/
wget https://www.python.org/ftp/python/3.13.7/Python-3.13.7.tgz
sudo apt update
sudo apt install -y \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev  \
    libsqlite3-dev \
    github

tar -xzvf Python-3.13.7.tgz 
cd Python-3.13.7/
./configure --enable-optimizations # may take an hour
sudo make altinstall

# make default
sudo rm /usr/bin/python
sudo ln -s /usr/local/bin/python3.13 /usr/bin/python
sudo rm /usr/local/bin/python
sudo ln -s /usr/local/bin/python3.13 /usr/local/bin/python

# add poetry
# python -m pip install poetry


# github
sudo apt install gh
