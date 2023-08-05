# Artifact Evaluation for "Automatic Testing for Correct Operations of Cloud Systems" ([SOSP'23 AE #77](https://sosp23ae.hotcrp.com/paper/77))

# 1. Artifact Goals

The instructions will reproduce the key results in Tables 5, 6, 7, and 8 in Section 6 of the submission. That is, the following instructions will lead you to (1) reproduce all 56 bugs found by Acto and oracles needed to find them, and (2) reproduce the test generation.

The entire artifact process can take around 2 hours if run with a concurrency of 16 workers (e.g., using the CloudLab machine we suggest); it will take about 17 hours if running sequentially (with no concurrent worker).

If you have any questions, please contact us via email or HotCRP.

# 2. Prerequisites

## Setting up [CloudLab](https://www.cloudlab.us/) machines

If you are a first timer of CloudLab, we encourage you to read the CloudLab doc for an overview of how Artifact Evaluation is generally conducted on CloudLab.

[CloudLab For Artifact Evaluation](https://docs.cloudlab.us/repeatable-research.html#%28part._aec-members%29)

If you do not already have a CloudLab account, please apply for one following this [link](https://www.cloudlab.us/signup.php),
  and ask the SOSP AEC chair to add you to the SOSP AEC project.

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

The start up would take around 10 minutes.
Please patiently wait for both the `Status` and `Startup` become `Ready`.
After that, Acto is installed at the `workdir/acto` directory under your `$HOME` directory.

Access the machine using `ssh` or through the `shell` provided by the CloudLab Web UI.
Please proceed to the [Kick-the-tire Instructions](#3-kick-the-tire-instructions-10-minutes) to validate.

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

The start up would take around 10 minutes.
Please patiently wait for both the `Status` and `Startup` becomes `Ready`.
After that, Acto is installed at the `workdir/acto` directory under your $home directory.

Access the machine using `ssh` or through the `shell` provided by the CloudLab Web UI.
Please proceed to the [Kick-the-tire Instructions](#3-kick-the-tire-instructions-10-minutes) to validate.


## Setting up local environment (skip this if using the CloudLab profile)
<details><summary>Click to show details</summary>
 
* A Linux system with Docker support
* Python 3.8 or newer
* Install `pip3` by running `sudo apt install python3-pip`
* Install [Golang](https://go.dev/doc/install)
* Clone the repo recursively by running `git clone --recursive --branch sosp-ae https://github.com/xlab-uiuc/acto.git`
* Install Python dependencies by running `pip3 install -r requirements.txt` in the project
* Install `Kind` by running `go install sigs.k8s.io/kind@v0.20.0`
* Install `Kubectl` by running `curl -LO https://dl.k8s.io/release/v1.22.9/bin/linux/amd64/kubectl` and `sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl`
* Configure inotify limits (need to rerun after reboot)
  * `sudo sysctl fs.inotify.max_user_instances=1024`
  * `sudo sysctl fs.inotify.max_user_watches=1048576`

</details>

# 3. Kick-the-tire Instructions (10 minutes)

We prepared a simple example –  reproducing a bug found by Acto – to help check obvious setup problems. 

First, build the dependant modules:

```sh
cd ~/workdir/acto/
make
```

Then, reproduce the OCK-RedisOp-287 bug by running:

```sh
python3 reproduce_bugs.py --bug-id rdoptwo-287
```

Expected results:

```text
Reproducing bug rdoptwo-287 in OCK-RedisOp!
Preparing required images...
Deleting cluster "acto-0-cluster-0" ...
Creating a Kind cluster...
Deploying operator...
Operator deployed
Bug rdoptwo-287 reproduced!
Bug category: undesired_state
```

# 4. Full Evaluation Instructions (2+ hours)

## Reproducing Tables 5, 6, 7

To reproduce the 56 bugs in Table 5, please execute the tests by running:

```sh
cd ~/workdir/acto/
make
python3 reproduce_bugs.py -n <NUM_WORKERS>
```

Using the c6420 profile we recommend, run the tests with 16 workers `-n 16` and it will take about 80 minutes to finish.

Using the c8220 profile we cecommend, run the tests with 8 workers `-n 8` and it will take about 3 hours to finish.

**Caution**: running too many workers at the same time may overload your machine, and Kind would fail to bootstrap Kubernetes clusters. If you are not running the experiment using our recommended CloudLab profile, please default the number of workers to `1`. Running this step sequentially takes approximately 17 hours.

<details><summary>What does the reproduce script do?</summary>For each bug, the reproduction code runs Acto with tests needed to reproduce the bug. It checks if every bug is reproducible and outputs Table 5. The code uses each bug’s consequence labels to reproduce Table 6. The code also checks which oracles are used by Acto to detect the bug, and reproduces Table 7.</details>

After it finishes, you will find `table5.txt`, and `table6.txt`, and `table7.txt` in the current directory.

The `table5.txt` should look like below:

```text
Operator         Undesired State    System Error    Operator Error    Recovery Failure    Total
-------------  -----------------  --------------  ----------------  ------------------  -------
CassOp                         2               0                 0                   2        4
CockroachOp                    3               0                 2                   0        5
KnativeOp                      1               0                 2                   0        3
OCK-RedisOp                    4               1                 3                   1        9
OFC-MongoDBOp                  3               1                 2                   2        8
PCN-MongoDBOp                  4               0                 0                   1        5
RabbitMQOp                     3               0                 0                   0        3
SAH-RedisOp                    2               0                 0                   1        3
TiDBOp                         2               1                 0                   1        4
XtraDBOp                       4               0                 1                   1        6
ZookeeperOp                    4               1                 0                   1        6
Total                         32               4                10                  10       56
```

The `table6.txt` should look like below:

```text
Consequence          # Bugs
-----------------  --------
System failure            5
Reliability issue        15
Security issue            2
Resource issue            9
Operation outage         18
Misconfiguration         15
```

The `table7.txt` should look like below:

```text
Test Oracle                                          # Bugs (Percentage)
---------------------------------------------------  ---------------------
Consistency oracle                                   23 (41.07%)
Differential oracle for normal state transition      25 (44.64%)
Differential oracle for rollback state transition    10 (17.86%)
Regular error check (e.g., exceptions, error codes)  14 (25.00%)
```

## Reproducing Table 8 (1 minute)

For Table 8, we reproduce "#Ops" (Column 5) Acto generated during test campaigns in our evaluation. We provide test data we collected in our evaluation of Acto and reproduce Table 8 based on the evaluation data.

Note: Running test campaigns of all the 11 operators with a single worker would take around 1,920 machine hours, or 160 hours with the Cloudlab Clemson c6420 machine with the level of parallelism in our evaluation. We provide instructions in the next section if you’d like to run that.


To collect #Ops Acto generated for each test campaign, run the following script,

```sh
python3 collect_number_of_ops.py
```

The output should look like this:

```text
Operator         # Operations
-------------  --------------
CassOp                    568
CockroachOp               371
KnativeOp                 774
OCK-RedisOp               597
OFC-MongoDBOp             434
PCN-MongoDBOp            1749
RabbitMQOp                394
SAH-RedisOp               718
TiDBOp                    824
XtraDBOp                 1950
ZookeeperOp               740
```

## Running all the test campaigns of all the operators (Optional)
<details><summary>Click to show detailed instructions</summary>

Please note that running all the test campaigns on the CloudLab Clemson c6420 could take 160 machine hours. In our evaluation, we did all the entire runs progressively and ran different test campaigns on different machines at the same time, with a cluster of 10 CloudLab machines. We suggest you reserve 10 machines, instead of doing it with one machine.

You can refer to [test_campaign.md](test_campaign.md) for detailed commands for running each test campaign.

If you would like to try out an end-to-end test campaign, you can do it with the following commands (taking the RabbitMQ operator as an example).

Build the dependant modules as in previous sections if you haven't done so:

```sh
cd ~/workdir/acto/
make
```

Run the test campaign:

```sh
python3 -m acto --config data/rabbitmq-operator/config.json --num-workers 16 --workdir testrun-rabbitmq
```

</details>

