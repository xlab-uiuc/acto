# Frequently Asked Questions

### Error message: `k8sutil.so: cannot open shared object file: No such file or directory.`

The `k8sutil.so` is a shared object used by Acto. To produce this shared object, in the acto’s root directory, run `make`

### Acto only supports deploying operators using YAML files, but my operator is deployed with Helm/Kustomize. How should I write the deploy section of the config file?
  You can produce the equivalent YAML files from the Helm chart/Kustomize using the following commands
- [helm template](https://helm.sh/docs/helm/helm_template/) / [helm get manifest](https://helm.sh/docs/helm/helm_get_manifest/)
- [kustomize build](https://kubectl.docs.kubernetes.io/references/kustomize/cmd/build/)
### How do I know which Kubernetes release I should use for my operator (i.e. the `kubernetes_version` field in the config.json)?
You should be able to find the client’s version in the operator’s version control file. For example, Golang operators have `client-go` dependency in their go.mod files. You can use the `client-go`'s version to get the appropriate Kubernetes version following their semver practice: [https://github.com/kubernetes/client-go?tab=readme-ov-file#kubernetes-tags](https://github.com/kubernetes/client-go?tab=readme-ov-file#kubernetes-tags)
### How many have Acto generated for the operator? How many tests are there left?
At the beginning of the `test.log`, you can find a line in the log of the format `Generated %d test cases to run`
To get the number of tests left to run, you can do a keyword search in the log for `Progress [` to get the number of tests left for a worker.

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
