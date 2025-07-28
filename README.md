# Artifact Evaluation for "Who Watches the Watchers? On the Reliability of Softwarizing Cloud Application Management" ([NSDI'26 Spring AE #14]())

# 1. Artifact Goals

This artifact will reproduce all the quantitative findings and tables in the operator
  failure study and the OAT tool's evaluation result (Table 7).

This artifact includes (1) the dataset of 412 failure cases of 13 popular
  Kubernetes operators with instructions to reproduce the findings and tables and
  (2) reproduction instructions for the 86 bugs found by OAT.


The entire artifact process can take around XXX hours if run with a concurrency of 8 workers (e.g., using the CloudLab machine we suggest); it will take about 17 hours if running sequentially (with no concurrent worker).

If you have any questions, please contact us via email or HotCRP.

# 2. Prerequisites for OAT

## Setting up [CloudLab](https://www.cloudlab.us/) machines

If you are a first timer of CloudLab, we encourage you to read the CloudLab doc for an overview of how Artifact Evaluation is generally conducted on CloudLab.

[CloudLab For Artifact Evaluation](https://docs.cloudlab.us/repeatable-research.html#%28part._aec-members%29)

If you do not already have a CloudLab account, please apply for one following this [link](https://www.cloudlab.us/signup.php),
  and ask the SOSP AEC chair to add you to the SOSP AEC project. Please let us know if you have trouble accessing cloudlab, we can help set up the experiment and give you access.

We recommend you to use the machine type, [c6420](https://www.cloudlab.us/instantiate.php?project=Sieve-Acto&profile=acto-cloudlab&refspec=refs/heads/main) (CloudLab profile), which was used by the evaluation. Note that the machine may not be available all the time. You would need to submit a resource reservation to guarantee the availability of the resource.
You can also use the alternative machine type via our profile, [c8220](https://www.cloudlab.us/p/Sieve-Acto/acto-cloudlab?refspec=refs/heads/c8220). The c8220 machine is available most of the time, but has less memory than c6420.

Note that our results in the evaluation are all produced using the [c6420](https://www.cloudlab.us/instantiate.php?project=Sieve-Acto&profile=acto-cloudlab&refspec=refs/heads/main) profile.

Below, we provide three ways to set up the environment:
1. [Set up environment on CloudLab c6420 using the profile (recommended)](#setting-up-environment-for-cloudlab-machine-c6420-using-the-profile-recommended)
2. [Set up environment on CloudLab c8220 using the profile](#setting-up-environment-for-cloudlab-machine-c8220-using-the-profile)
3. [Set up environment on a local machine](#setting-up-local-environment-skip-this-if-using-the-cloudlab-profile)

## Reserve nodes with preferred hardware type

To reserve machines, click the “Reserve Nodes” tab from the dropdown menu from the “Experiments” tab at top left corner. Select “CloudLab Clemson” for the cluster, “c6420” as the hardware, and “1” for the number of nodes. Specify the desired time frame for the reservation, and click “Check”. The website will check if your reservation can be satisfied and then you can submit the request. The request will be reviewed by CloudLab staff and approved typically on the next business day.

[Resource Reservation](http://docs.cloudlab.us/reservations.html)

Note: Reservation does not automatically start the experiment.

## Setting up environment for CloudLab machine c6420 using the profile (recommended)

We provide CloudLab profile to automatically select the c6420 as the machine type and set up
  all the environment.

To use the profile, follow the [link](https://www.cloudlab.us/instantiate.php?project=Sieve-Acto&profile=acto-cloudlab&refspec=refs/heads/main)
and keep hitting `next` to create the experiment.
You should see that CloudLab starts to provision the machine and our profile will run a StartUp
  script to set the environment up.

The start up would take around 15 minutes.
Please patiently wait for "Status" to become `Ready` and "Startup" to become `Finished`.
After that, Acto is installed at the `workdir/acto` directory under your `$HOME` directory.

Access the machine using `ssh` or through the `shell` provided by the CloudLab Web UI.
Please proceed to the [Kick-the-tire Instructions](#3-kick-the-tire-instructions-10-minutes) to validate.

### Seeing `Exited (2)` in the "Startup" column?

<details><summary>Click to show details</summary>

There could sometimes be transient network issues within the CloudLab cluster, which prevent e.g. `pip install` in the startup scripts from functioning as expected.

To circumvent the problem, either

1. Recreate the experiment using the same profile, or
2. SSH into the machine and manually rerun the startup:

    ```sh
    sudo su - geniuser
    bash /local/repository/scripts/cloudlab_startup_run_by_geniuser.sh
    exit
    ```

</details>


### Seeing error message from CloudLab `No available physical nodes of type c6420 found (1 requested)`?
<details><summary>Click to show details</summary>

This means that currently there is no c6420 machines available for experiments.
Please check the [Reserve nodes with preferred hardware](#reserve-nodes-with-preferred-hardware-type) section or check back later.

</details>

## Setting up environment for CloudLab machine c8220 using the profile

We provide CloudLab profile to automatically select the c8220 as the machine type and set up
  all the environment, in case the c6420 machine is not available at the time of starting experiment,
  or reviewers do not have enough time to make a resource reservation.

To use the profile, follow the [link](https://www.cloudlab.us/p/Sieve-Acto/acto-cloudlab?refspec=refs/heads/c8220)
and keep hitting `next` to create the experiment.
You should see that CloudLab starts to provision the machine and our profile will run a StartUp
  script to set the environment up.

The startup would take around 20 minutes.
Please patiently wait for "Status" to become `Ready` and "Startup" to become `Finished`.
After that, Acto is installed at the `workdir/acto` directory under your `$HOME` directory.

Access the machine using `ssh` or through the `shell` provided by the CloudLab Web UI.
Please proceed to the [Kick-the-tire Instructions](#3-kick-the-tire-instructions-10-minutes) to validate.


## Setting up local environment (skip this if using the CloudLab profile)
<details><summary>Click to show details</summary>

* A Linux system with Docker support
* Python 3.12 or newer
* Install `pip3` by running `sudo apt install python3-pip`
* Install [Golang](https://go.dev/doc/install)
* Clone the repo recursively by running `git clone --recursive --branch nsdi26-ae https://github.com/xlab-uiuc/acto.git`
* Install Python dependencies by running `pip3 install -r requirements-dev.txt` in the project
* Install `Kind` by running `go install sigs.k8s.io/kind@v0.21.0`
* Install `Kubectl` by running `curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"` and `sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl`
* Configure inotify limits (need to rerun after reboot)
  * `sudo sysctl fs.inotify.max_user_instances=1024`
  * `sudo sysctl fs.inotify.max_user_watches=1048576`

</details>

# 3. Kick-the-tire Instructions for OAT (10 minutes)

We prepared a simple example – reproducing a bug found by OAT – to help check obvious setup problems.

First, build the dependent modules:

```sh
cd ~/workdir/acto/
make
```

Then, reproduce the MariaDBOp-863 bug by running:

```sh
python3 reproduce_bugs.py --bug-id mariadbop-863
```

Expected results:

```text
Reproducing bug mariadbop-863 in MariaDBOp!
Preparing required images...
Deleting cluster "acto-0-cluster-0" ...
Deleted nodes: ["acto-0-cluster-0-worker2" "acto-0-cluster-0-worker4" "acto-0-cluster-0-worker5" "acto-0-cluster-0-worker3" "acto-0-cluster-0-worker" "acto-0-cluster-0-control-plane"]
Creating a Kind cluster...
Creating cluster "acto-0-cluster-0" ...
...

Deploying operator...
Operator deployed
pod/mariadb-writer created
Bug mariadbop-863 reproduced!
Bug category: Operation Semantics
```

# 4. Full Evaluation Instructions

## 4.1 Operator Failure Study

You can view the tables and findings reproduced using Jupyter notebooks here: [https://github.com/xlab-uiuc/acto/blob/nsdi26-ae/study.ipynb](https://github.com/xlab-uiuc/acto/blob/nsdi26-ae/study.ipynb)

**Operator Failure Dataset:** https://github.com/xlab-uiuc/acto/blob/nsdi26-ae/nsdi26ae.csv

## 4.2 OAT Evaluation Instructions (2+ hours)

To reproduce the 86 bugs in Table 5, please execute the tests by running:

```sh
cd ~/workdir/acto/
make
python3 reproduce_bugs.py -n <NUM_WORKERS>
```

Using the c6420 profile we recommend, run the tests with 16 workers `-n 8` and it will take about XX minutes to finish.

Using the c8220 profile we recommend, run the tests with 8 workers `-n 4` and it will take about XX hours to finish.

We suggest starting this long-running experiment in a tmux or screen session.

**Caution**: running too many workers at the same time may overload your machine, and Kind would fail to bootstrap Kubernetes clusters. If you are not running the experiment using our recommended CloudLab profile, please default the number of workers to `1`. Running this step sequentially takes approximately 24 hours.

<details><summary>What does the reproduce script do?</summary>For each bug, the reproduction code runs OAT with tests needed to reproduce the bug. It checks if every bug is reproducible and outputs Table 5. </details>
