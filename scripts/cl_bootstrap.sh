#!/bin/bash

# Get a sense of what's happenning at this timing
echo hello      | sudo tee /etc/hello/hello
whoami          | sudo tee /etc/hello/whoami
pwd             | sudo tee /etc/hello/pwd
ls /users       | sudo tee /etc/hello/users
cat /etc/passwd | sudo tee /etc/hello/passwd

sudo apt update
sudo apt -y install software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt -y install ansible
ansible-galaxy collection install ansible.posix
ansible-galaxy collection install community.general
