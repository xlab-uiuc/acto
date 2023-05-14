# Acto: Automatic Correctness Testing for (Kubernetes) Operators


## Overview
Many cloud systems today have operators to manage them atop the Kubernetes platform.
These operators automate important management
tasks, e.g., software upgrades, configuration updates, and autoscaling.
Even for the same cloud system, different operators
are implemented by commercial vendors and open-source
communities to support different practices and environments

Acto is a tool to help developers test the correctness of their operators.
It tests operation correctness by performing end-to-end (e2e) testing of cloud-native operators together with the managed systems. 
To do so, Acto continuously generates new operations during a test campaign.
Then, Acto’s oracles check if the operator always correctly reconciles the system from each current state to the desired state, or raises an alarm otherwise.

To use Acto, developers need to port their operators by providing a way to deploy the operators.
Acto runs in two modes, blackbox mode and whitebox mode.
For blackbox mode, Acto only needs the deployment script for the operators.
For whitebox mode, Acto additionally needs the source code information.
We list detailed porting steps [here](docs/port.md).

Acto generates syntactically valid desired state declarations by parsing the CRD of each operator, which contains constraints like type, min/max values(for numeric types), length (for string type), regular-expression patterns, etc.
Acto generates values which satisfy predicates, in the form of property dependencies. In blackbox mode, Acto infers the dependencies through naming conventions. In whitebox mode, Acto infers the dependencies using control-flow analysis on the source code.

## Prerequisites
- Golang
- Python dependencies
    - `pip3 install -r requirements.txt`
- [k8s Kind cluster](https://kind.sigs.k8s.io/)  
    - `go install sigs.k8s.io/kind@v0.14.0`
- kubectl
    - [Installation](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)
- helm
    - [Installing Helm](https://helm.sh/docs/intro/install/)

## Usage
To run the test:  
```
python3 acto.py \
  --config CONFIG, -c CONFIG
                        Operator port config path
  --num-workers NUM_WORKERS
                        Number of concurrent workers to run Acto with
  --workdir WORK_DIR
                        The directory where acto writes results
```

## Example
For example, to run Acto to test the cass-operator, just run
```sh
python3 acto.py --config data/cass-operator/config.json --num-workers 4 --workdir testrun-cass
```

Acto will first generate a test plan using the operator's CRD and the semantic information. The test plan is serialized at `testrun-cass/testplan.json`. Note that Acto does not run the tests according to the order in the `testplan.json`, the tests are run in a random order at runtime.

Acto then constructs the number of Kubernetes clusters according to the `--num-workers` argument,
  and start to run tests.
Tests are run in parallel in separate Kubernetes clusters.
Under the `testrun-cass` directory, Acto creates directories `trial-XX-YYYY`. `XX` corresponds to the worker id, i.e. `XX` ranges from `0` to `3` if there are 4 workers.
`YYYY` starts from `0000`, and Acto increments `YYYY` every time it has to restart the cluster. This means every step inside the same `trial-xx-yyyy` directory run in the same instance of Kubernetes cluster.

Inside each `trial-XX-YYYY` directory, Acto writes `mutated-Z.yaml` files.
These files are the CRs Acto submitted to Kubernetes to run the state transitions.
Concretely, Acto first applies `mutated-0.yaml`, and wait for the system to converge,
  and then applies `mutated-1.yaml`, and so on.
After each step, Acto collects the system state and store it as `system-state-Z.json`.
The command line result and operator log are also collected and stored as `cli-output-Z.log` and `operator-Z.log`.
For quick debugging purposes, Acto serializes the delta of each step and its previous step to `delta-Z.log`. It contains the delta in the input and the delta in the system state. 
But `delta-Z.log` is not essential, it can be computed from `mutated-Z.yaml` and `system-state-Z.log`.

Acto reports the runtime oracle result and writes them to `generation-Z-runtime.json`.
Note that Acto writes such files even if the oracle does not report an alarm.
The file stores the result of different oracles in Acto.

We provide a post-processing script to gather all the alarms into a csv file for alarm inspection.
After all tests finish, run
```sh
python3 checker.py --config data/cass-operator/config.json --num-workers 8 --testrun-dir testrun-cass
```
to post-process all the results.
We run this post-process step because previously we wanted to test the false alarm
  rate under different feature gates.
This post-processing step writes `post-result-Z-{FEATURE}.json` files.
Since now the feature gate has become irrelavent,
  the `post-result-Z-dependency_analysis.json` is the only relevant one.

Since Acto writes oracle result files no matter if there is an alarm or not,
  it is not very efficient to go through all the files and inspect all the alarms.
So we provide a script to collect all the alarms into an xlsx file:
```sh
python3 scripts/feature_results_to_csv.py --testrun-dir testrun-cass
```
It generates the `result.xlsx` file under the `testrun-cass` which contains
  all the oracle results.
You can easily inspect the alarms by importing it into Google Sheet or Excel
  and filter by `alarm==True`.


## Known Issues
- ([A Known Issue of Kind](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files)) Failed cluster creation when using the multiple worker functionality by specifying `--num-workers`.

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

## Example:   
**rabbitmq-operator**:  
```console
python3 acto.py --config data/rabbitmq-operator/config.json
                --num-workers 4
```

## Reproduce previously found bugs
Reproduction utility enables Acto to reproduce previously found bugs by taking a folder that contains previously generated CRs (i.e. mutated files) as input and directly deploying each CR. In this way, to reproduce a bug in a certain operator, Acto can just run a single testcase instead of running all testcases for that operator.

Usage:
```console
python3 reproduce.py --reproduce-dir <path to the folder containing CRs> --config <path to corresponding config.json>
```

## Porting operators
Acto aims to automate the E2E testing as much as possible to minimize users' labor.

Currently, porting operators still requires some manual effort, we need:
1. A way to deploy the operator, the deployment method needs to handle all the necessary prerequisites to deploy the operator, e.g. CRD, namespace creation, RBAC, etc. Current we support three deploy methods: `yaml`, `helm`, and `kustomize`. For example, rabbitmq-operator uses `yaml` for deployment, and the [example is shown here](data/rabbitmq-operator/operator.yaml)
2. A seed CR yaml serving as the initial cr input. This can be any valid CR for your application. [Example](data/rabbitmq-operator/cr.yaml)

## Known Limitations 
* https://github.com/xlab-uiuc/acto/issues/121
* https://github.com/xlab-uiuc/acto/issues/120

## Next Steps 
* https://github.com/xlab-uiuc/acto/issues/131


## Running Acto on good machines
Acto supports multi-cluster parallelism, which in theory makes Acto scale perfectly.
However, it turns out to be not that perfect when I tried to run Acto on a CloudLab 220-g5 machine.

The machine has 40 cores, 192 GB RAM, and a 500 GB SSD. I tried to run Acto with 8 clusters, and all
of them failed, because it takes the operators more than 5 minutes to get ready. Every cluster becomes
extremely slow, liveness probe fails very often causing pods being recreated all the time. I found
out that Acto is IO-bound, meaning the performance is bottled-necked by the speed of disk READ/WRITE.

We usually have 2 GB of images to preload into each cluster node, and we have 4 nodes for each cluster.
With 8 clusters, it means the machine needs to preload ~20GB * 8 content to the disk, and then read
some of them into memory to start running 4 * 8 Kubernetes. During all this time, CPU and memory are
moslty idle and SSD is at full-load all the time.

To mitigate this issue, there are two directions:
1. Reduce the size of the preload images
  - There are some redundent images in the image archive, we can remove them
  - Reduce the number of nodes in the cluster
  - Switch to k3s, which is a lightweight version of k8s
2. Mount docker's workdir in tmpfs on the RAM
  - Since we have 192 GB RAM on the machine, we can put docker's workdir in RAM to avoid the IO
  bottleneck

## Measure code coverage for Acto
Golang does not have many tools for measuring code coverage except the native `go test` util.
However, `go test` does not support measuring code coverage for E2E tests, it only supports 
measuring code coverage on unit/integration level.

We use a series of hacks to measure the code coverage for Acto:
1. Create a new file called `main_test.go` under the same directory with the `main.go`, the `main_test.go` 
should contain one unittest which calls the `main` function. In this way, we created a virtual
unittest which just runs the `main` function, essentially an E2E test.
2. Next, we need to compile this unittest into a binary and build a docker image on it. Luckily, 
`go test` supports `-c` flag which compiles the unittest into a binary to be run later instead of 
running it immediately. We then modify the `Dockerfile` to change the build command from `go build ...`
to `go test -c ...` with approriate flags. Along with the build flags, we also pass in the test flags
such as `-coverpkg -cover`.
3. Having the test binary is not enough, we need to pass in a flag when running the binary to redirect 
the coverage information to a file. To do this, we need to create a shell script which exec the binary 
with the `-test.coverprofile=/tmp/profile/cass-operator-``date +%s%N``.out` flag and make this shell 
script the entrypoint of the docker image.

## Next steps
- [ ] Alarm grouping utility
- [ ] Annotation support for false alarm
- [ ] Integrate with Augeas (Augeas only support reading files, while we want to parse raw strings"