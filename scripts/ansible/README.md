# Ansible playbook to automatically configure environment for Acto to run on a baremetal machine

To run the script, you first need an `ansible_hosts` file. Each line in the file should contain
a worker in your cluster. See https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html
for details.

An example:

```ini
c220g5-110417.wisc.cloudlab.us ansible_connection=ssh ansible_user=tylergu ansible_port=22
c220g5-110418.wisc.cloudlab.us ansible_connection=ssh ansible_user=tylergu ansible_port=22
```

If you haven't installed `ansible-playbook` on your control node, run

```sh
pip3 install ansible
ansible-galaxy collection install ansible.posix
ansible-galaxy collection install community.general
```

Then just run

```sh
ansible-playbook -i ansible_hosts configure.yaml
```

and the proper environment will be set up for the workers.

Note: because some system packages in some older distro (e.g. Ubuntu 20.04)
    requires python3 to point to Python3.8,
    and Acto currently requires Python3.10,
    the `configure.yaml` uses the `python-venv.yaml` to install the
    python environment in the `$HOME/workdir/acto/venv`.
    To use the venv, (for bash) run `source $HOME/workdir/acto/venv/bin/activate`
    before running Acto.
    Optionally, `python-venv.yaml` can be swapped to `python.yaml` playbook
    to directly install the environment under the system python environment.
