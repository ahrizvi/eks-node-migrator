<p align="left">
  <img height="100px" src="https://raw.githubusercontent.com/ahrizvi/eks-node-migrator/main/logo.png"  alt="EKS Node Migrator">
</p>

# EKS Node Migrator

EKS Node Migrator is a utility to gracefully drain / cordon self-managed EKS nodes in an EKS cluster. 

- [EKS Node Migrator](#eks-node-migrator)
- [Intro](#intro)
  - [Requirements](#requirements)
  - [Installation](#installation)
    - [From PyPi](#from-pypi)
    - [From source](#from-source)
  - [Usage](#usage)
  - [Configuration](#configuration)
  - [Examples](#examples)
  - [Docker](#docker)
  - [License](#license)


<a name="intro"></a>
# Intro

EKS Node Migrator is a utility for gracefully draining the desired nodegroups in an EKS cluster in a rolling manner. This tool is specifically focused on scanerio where additional nodegroups are provisioned in the clusters and workload is to be shifted from the older nodegroups to the newer ones. It can be specially useful in the case when a cluster is provisioned with new nodegroups based on SPOT instances and older nodegroups are to be depcreated. This tool will only take care of node drain / cordon process, scaling down the ASGs and / or removing the nodes from the cluster is not part of the process at the momment.

To achieve this, it performs the following actions:

* Finds a list of desired ASGs and node hostnames via provided nodegroup and cluster name
* Stores the node details on which the target 'action' is to be performed
* Perform drain / cordon operations on the stored list of nodes with provided nodegroup in a rolling manner
* During the drain/cordon process, the tool keeps checking the cluster workload health (POD health), bad health for longer duration halts the process 
* Ensures the ASGs are healthy and that the new nodes have joined the EKS cluster
* The tool is designed to work on one nodegroup in the cluster at a time

This tool is inspired by https://github.com/hellofresh/eks-rolling-update

<a name="requirements"></a>
## Requirements

* [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) installed
* `KUBECONFIG` environment variable set, or config available in `${HOME}/.kube/config` per default
* AWS credentials [configured](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#guide-configuration)

<a name="installation"></a>
## Installation

### From PyPi
```
$ mkdir ~/apps
$ mkdir ~/apps/eks-node-migrator
$ cd ~/apps/eks-node-migrator
$ virtualenv .env
$ source .env/bin/activate
(.env)$ pip install eks-node-migrator

$ cd /usr/local/bin
$ sudo ln -s ~/apps/myutil/.env/bin/eks_node_migrator.py
```

### From source

```
virtualenv -p python3 venv
source venv/bin/activate
pip3 install -r requirements.txt
```

<a name="usage"></a>
## Usage

```
usage: eks_node_migrator.py [-h] --cluster_name CLUSTER_NAME --nodegroup NODEGROUP --action ACTION

The tool to perform eks node drain/cordon ops

optional arguments:
  -h, --help            show this help message and exit
  --cluster_name CLUSTER_NAME, -c CLUSTER_NAME
                        the cluster name to perform drain/cordon operation on
  --nodegroup NODEGROUP, -ng NODEGROUP
                        the nodegroup name to perform drain/cordonupdate on
  --action ACTION, -a ACTION
                        the action to be performed i.e. drain or cordon
```

Example:

```
eks_node_migrator.py -c my-eks-cluster -ng monitoring -a cordon

eks_node_migrator.py -c my-eks-cluster -ng monitoring -a drain
```

## Configuration

| Environment Variable      | Description                                                                                                           | Default                                  |
|---------------------------|-----------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| AWS_DEFAULT_REGION        | Default AWS Region to execute the script on                                                                           | eu-west-1                                |
| BETWEEN_NODES_WAIT        | Number of seconds to wait after removing a node before continuing on                                                  | 0                                        |
| K8S_CONTEXT               | Context from the Kubernetes config to use. If this is left undefined the current-context is used                      | None                                     |
| K8S_PROXY_BYPASS          | Set to true to ignore HTTPS_PROXY and HTTP_PROXY and disable use of any configured proxy when talking to the K8S API  | False                                    |
| EXTRA_DRAIN_ARGS          | Additional space-delimited args to supply to the `kubectl drain` function, e.g `--force=true`. See `kubectl drain -h` | ""                                       |


## Examples

* Apply Changes

```
$ python eks_node_migrator.py --cluster_name YOUR_EKS_CLUSTER_NAME --nodegroup WORKER-NG-01 --action cordon
```

* Environment Variable

In order to modify default values for env varibales, please use it by exporting it the as follow:

```
$ export  BETWEEN_NODES_WAIT=30  
```

* Configure tool via `.env` file

Rather than using environment variables, you can use a `.env` file within your working directory to load 
updater settings. e.g:

```
$ cat .env
BETWEEN_NODES_WAIT=30
```

<a name="docker"></a>
## Docker

Please feel free to use the included [Dockerfile](Dockerfile) to build your own image.

```bash
make docker-dist version=1.0.DEV
```

After building the image, run using the command
```bash
docker run -ti --rm \
  -e AWS_DEFAULT_REGION \
  -e AWS_PROFILE \
  -v "${HOME}/.aws:/root/.aws" \
  -v "${HOME}/.kube/config:/root/.kube/config" \
  eks-node-migrator:latest \
  -c beta-spot-dev-sre-eks \
  -ng worker-ng-spot-1 \
  -a drain

```

Pass in any additional environment variables and options as described elsewhere in this file.

<a name="licence"></a>
## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details
