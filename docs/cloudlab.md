# CloudLab getting started guide

## 1 Prerequisites

First, submit an account request to CloudLab (https://www.cloudlab.us/). Things to note:

- If you're an internal member, select "Join Existing Project" and type: `Sieve-Acto`. Otherwise, you'll have to join other existing projects or create a new one, which is not detailed here.
- The username and key you provide will be used for SSH login

Wait for the admin to approve your account. Once you are able to login, familiarize yourself with the web-based dashboard, and [the concept of *profiles* and *experiments*](https://docs.cloudlab.us/basic-concepts.html).

Although you should be able to log in to any machine instantiated by your project collaborators (i.e. a Linux user will be automatically created for you on every machine with `authorized_keys` set up), for us (`Sieve-Acto`), the current practice is to let everyone run code **on their own experiments**.

Next you'll prepare the dependencies either manually ([section 2](#2-manually-set-up-the-dependencies)) or automatically ([section 3](#3-automatically-set-up-the-dependencies), recommended).

## 2 Manually set up the dependencies

<details><summary>Click to show details</summary>

### 2.1 Create CloudLab experiments

Launch an experiment via the web dashboard:

1. Click "Experiments" -- "Start Experiment". The default selected profile should be `small-lan`. "Next".
2. Enter/Choose parameters:
    - "Select OS image": `UBUNTU 20.04`
    - "Optional physical node type": `c6420`
    - Leave other parameters as default. (Especially those regarding temporary filesystem -- this will be handled after provisioning using Ansible.)
3. "Next". Give your experiment a name. "Next". "Finish".

Wait for the provisioning to finish. The web dashboard will show you the server address, in the form of `<node>.<cluster>.cloudlab.us`. E.g. `clnode123.clemson.cloudlab.us`.

### 2.2 Install the dependencies with Ansible

You are going to manage CloudLab machines with Ansible from a controller node. This "controller" can be your local machine, or one of the CloudLab machines themselves.

**On your controller node**:

Install Ansible:

```shell
sudo apt update
sudo apt -y install software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt -y install ansible
ansible-galaxy collection install ansible.posix
ansible-galaxy collection install community.general
```

Clone the Ansible scripts:

```shell
git clone https://github.com/xlab-uiuc/acto-cloudlab.git /tmp/acto-cloudlab
```

Set up `ansible_hosts` file (**remember to replace the placeholders with your real domain and user name**):

```shell
domain="clnodeXXX.clemson.cloudlab.us"
user="alice"

cd /tmp/acto-cloudlab/scripts/ansible/
echo "$domain ansible_connection=ssh ansible_user=$user ansible_port=22" > ansible_hosts
```

> If the controller is a CloudLab machine too, this step can be automated:
>
> ```shell
> sudo apt -y install xmlstarlet
>
> component_name=$( geni-get portalmanifest | xmlstarlet sel -N x="http://www.geni.net/resources/rspec/3" -t -v "//x:node/@component_id" )
> cluster_domain=$( echo $component_name | cut -d '+' -f 2 )
> node_subdomain=$( echo $component_name | cut -d '+' -f 4 )
> domain="${node_subdomain}.${cluster_domain}"
> user=$( geni-get user_urn | rev | cut -d '+' -f -1 | rev )
>
> cd /tmp/acto-cloudlab/scripts/ansible/
> echo "$domain ansible_connection=ssh ansible_user=$user ansible_port=22" > ansible_hosts
> ```
>
> Or even simpler, use `127.0.0.1` directly:
>
> ```shell
> cd /tmp/acto-cloudlab/scripts/ansible/
> echo 127.0.0.1 > ansible_hosts
> ```

(Only if the controller is a CloudLab machine too) work around the key authentication:

```shell
ssh-keygen -b 2048 -t rsa -f ~/.ssh/id_rsa -q -N "" && cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
```

Finally, run the Ansible scripts to install dependencies:

```shell
ansible-playbook -i ansible_hosts configure.yaml
```

</details>

(Only if the controller is a CloudLab machine too) log out before jumping to section 4 and logging in again.

Go to [section 4](#4-run-acto).

## 3 Automatically set up the dependencies

Everything needed to install the dependencies (see section 2) is included in [a CloudLab profile](https://github.com/xlab-uiuc/acto-cloudlab), by which the same environment can be set up without manually entering any command.

Launch an experiment via the web dashboard:

1. Open this link: https://www.cloudlab.us/p/Sieve-Acto/acto-cloudlab?refspec=refs/heads/main. The default selected profile should be `acto-cloudlab`. "Next".
2. "Next". Give your experiment a name. "Next". "Finish".

Wait for provisioning and startup both to finish (i.e. under the "List View" tab, "Status" is `ready` and "Startup" is `Finished`). The web dashboard will show you the server address, in the form of `<node>.<cluster>.cloudlab.us`. E.g. `clnode123.clemson.cloudlab.us`.

## 4 Run Acto

Log in to the CloudLab machine, and run:

<!-- TODO this is now sosp-ae because of Ansible scripts in acto-cloudlab -->

```shell
cd ~/workdir/acto
make
python3 reproduce_bugs.py --bug-id rdoptwo-287
```
