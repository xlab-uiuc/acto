# Ansible playbook to automatically configure environment for Acto to run a baremetal machine
To run the script, you first need an `ansible_hosts` file. Each line in the file should contain
a worker in your cluster. See https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html
for details.

An example:
```ini
c220g5-110417.wisc.cloudlab.us ansible_connection=ssh ansible_user=tylergu ansible_port=22
c220g5-110418.wisc.cloudlab.us ansible_connection=ssh ansible_user=tylergu ansible_port=22
```

If you haven't installed `ansible playbook` on your control node, run
```sh
pip3 install ansible
ansible-galaxy collection install ansible.posix
ansible-galaxy collection install community.general
``` 

Then just run 
```
bash configure.sh
```
and the proper environment will be setup on the workers.
