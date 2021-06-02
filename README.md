### Pre-requisites
- Install [`doctl`](https://github.com/digitalocean/doctl) and set it up.
- Install [`kubectl`](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/).
- Install [`faas-cli`](https://docs.openfaas.com/cli/install/).
- Install [`artillery`](https://artillery.io/docs/guides/getting-started/installing-artillery.html).

### Usage
Run the `manage-cluster.py` script to create, list and delete systems under test, or SUT. After creating an SUT, the script prints out the command you need to run to in order to run the benchmarks.
