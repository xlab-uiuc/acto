# CloudLab getting started guide

## Create CloudLab experiments

First, submit an account request to CloudLab (https://www.cloudlab.us/). Things to note:

- Select "Join Existing Project" and type: `Sieve-Acto`
- The username and key you provide will be used for SSH login

Wait for the admin to approve your account. Once you are able to login, familiarize yourself with the web-based dashboard, and [the concept of *profiles* and *experiments*](https://docs.cloudlab.us/basic-concepts.html).

Although you should be able to login onto any machine instantiated by your project collaborators (i.e. a Linux user will be automatically created for you on every machine with `authorized_keys` set up), our current practice is to let everyone run code **on their own experiments**.

Launch an experiment via the web dashboard:

1. Click "Experiments" -- "Start Experiment". The default selected profile should be `small-lan`. "Next".
2. Enter/Choose parameters:
    - "Select OS image": `UBUNTU 20.04`
    - "Optional physical node type": `c6420`
    - Leave other parameters as default. (Especially those regarding temporary filesystem -- we'll deal with it after provisioning using Ansible.)
3. "Next". Give your experiment a name. "Next". "Next".

Wait for the provisioning to finish. The web dashboard will show you the server address, in the form of `clnodeXXX.clemson.cloudlab.us`.

## Configure CloudLab machines

We are going to manage CloudLab machines with Ansible **from our local machine**. (Ideally this "local machine" can be a CloudLab one too. However, the scripts were not designed to do so and may mess things up. For the time being, minor tweaks are needed in order to let them function properly in such cases.)

**On your local machine**:

```shell
#
# Install Ansible
#

# A Python virtual environment is encouraged, which is not detailed here though.
pip3 install ansible
ansible-galaxy collection install ansible.posix
ansible-galaxy collection install community.general

#
# Checkout the repository
#

cd ~
git clone https://github.com/xlab-uiuc/acto.git
cd acto/

#
# Prepare the CloudLab machine(s) with Ansible
#

cd scripts/ansible/
# TODO: replace the placeholders with your real domain and user name you
# obtained or submitted in the previous section
domain="clnodeXXX.clemson.cloudlab.us"
user="alice"
echo "$domain ansible_connection=ssh ansible_user=$user ansible_port=22" > ansible_hosts
ansible-playbook -i ansible_hosts configure.yaml
```

## Run Acto

Login onto **the CloudLab machine**, and run:

```shell
cd ~/acto
pip install -r requirements.txt # FIXME: see #247
make
python3 -m acto.reproduce \
        --reproduce-dir test/cassop-330/trial-demo \
        --config data/cass-operator/config.json
```
