#!/bin/bash

#
# Install Ansible
#

sudo apt update
sudo apt -y install software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt -y install ansible
ansible-galaxy collection install ansible.posix
ansible-galaxy collection install community.general

#
# Checkout the repository
#

cd /local/repository/
git checkout sosp-ae

#
# Prepare the CloudLab machine(s) with Ansible
#

cd scripts/ansible/
# By default the user will be the current one (geniuser)
echo 127.0.0.1 > ansible_hosts
# Work around the key authentication
ssh-keygen -b 2048 -t rsa -f ~/.ssh/id_rsa -q -N "" && cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
sed -i 's|git@github.com:xlab-uiuc/acto.git|https://github.com/xlab-uiuc/acto.git|' acto.yaml # FIXME: see #247
ansible-playbook -i ansible_hosts configure.yaml
