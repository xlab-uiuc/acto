# Known Limitations

### Failed cluster creation when using the multiple worker functionality by specifying `--num-workers`
([A Known Issue of Kind](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files))

This may be caused by running out of inotify resources. Resource limits are defined by fs.inotify.max_user_watches and fs.inotify.max_user_instances system variables. For example, in Ubuntu these default to 8192 and 128 respectively, which is not enough to create a cluster with many nodes.

To increase these limits temporarily, run the following commands on the host:
```shell
sudo sysctl fs.inotify.max_user_watches=524288
sudo sysctl fs.inotify.max_user_instances=512
```
To make the changes persistent, edit the file /etc/sysctl.conf and add these lines:
```shell
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
```
