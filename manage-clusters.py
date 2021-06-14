import logging
import subprocess
import time
from argparse import ArgumentParser
from pathlib import Path
from typing import Callable, Optional

import coloredlogs
from ruamel.yaml import YAML

logger = logging.getLogger()
coloredlogs.install(level="DEBUG", logger=logger)
yaml = YAML()


def run_command(
    command: str,
    capture_output: bool = False,
    success_condition: Optional[Callable[[str], bool]] = None,
) -> Optional[str]:
    logger.debug(f"Executing: {command}")
    if success_condition:
        while True:
            cp = subprocess.run(command, shell=True, capture_output=True)
            if success_condition(cp.stdout.decode("UTF-8")):
                break
            time.sleep(10)
    else:
        cp = subprocess.run(command, shell=True, capture_output=capture_output)
    if capture_output:
        return cp.stdout.decode("UTF-8")


def create_cluster(
    size: str, count: int, min_replicas: int, max_replicas: int, target_fips: float
) -> None:
    logger.info(f"Creating cluster with {count} {size} nodes")
    cluster_name = f"{size}-{count}"
    run_command(
        "doctl kubernetes cluster create "
        f"--count {count} --region blr1 --size {size} {cluster_name}"
    )
    cluster_id = run_command(
        f"doctl kubernetes cluster get {cluster_name} --format ID --no-header",
        capture_output=True,
    ).strip()
    logger.info(f"Cluster created, name: {cluster_name}, ID: {cluster_id}")
    time.sleep(10)

    logging.info("Installing OpenFaaS on cluster")
    run_command("arkade install openfaas --load-balancer --gateways 3 "
                "--set gateway.directFunctions=false --set async=false "
                "--set faasnetes.readTimeout=2m --set faasnetes.writeTimeout=2m "
                "--set gateway.readTimeout=2m --set gateway.writeTimeout=2m "
                "--set gateway.upstreamTimeout=2m")
    logging.info("Installing metrics-server on cluster")
    run_command("arkade install metrics-server")

    logger.info(f"Installing prometheus-adapter on cluster")
    run_command("helm repo update")
    run_command(
        "helm install prometheus-adapter prometheus-community/prometheus-adapter "
        "-f kubernetes/prometheus-adapter-values.yml",
    )

    logger.info("Exposing Prometheus service of OpenFaaS")
    run_command(
        "kubectl expose service prometheus -n openfaas --port=9090 --target-port=9090 "
        "--type=LoadBalancer --name=prometheus-external"
    )

    output = run_command(
        "kubectl get service prometheus-external -n openfaas --no-headers",
        capture_output=True,
        success_condition=lambda x: "pending" not in x,
    )
    prometheus = f"http://{output.split()[3]}:9090"
    logger.info(f"OpenFaaS Prometheus is available at: {prometheus}")

    logger.info("Log into OpenFaaS CLI")
    passwd = run_command(
        "echo $(kubectl -n openfaas get secret basic-auth -o "
        'jsonpath="{.data.basic-auth-password}" | base64 --decode)',
        capture_output=True,
    )
    if passwd:
        logger.info(f"OpenFaaS password is: {passwd}")
    output = run_command(
        "kubectl get services -n openfaas gateway-external --no-headers",
        capture_output=True,
        success_condition=lambda x: "pending" not in x,
    )
    gateway = f"http://{output.split()[3]}:8080"
    logger.info(f"OpenFaaS gateway is available at: {gateway}")
    run_command(f"faas-cli login -g {gateway} -u admin -p {passwd}")

    logger.info("Deploying function to OpenFaaS")
    run_command(f"faas-cli deploy -f function/primality.yml --gateway {gateway}")

    logger.info("Deploying HPA")
    hpa_config = yaml.load(Path("kubernetes/hpa-function-invocation-per-second.yml"))
    hpa_config["spec"]["minReplicas"] = min_replicas
    hpa_config["spec"]["maxReplicas"] = max_replicas
    hpa_config["spec"]["metrics"][0]["external"]["target"]["averageValue"] = target_fips
    yaml.dump(hpa_config, Path("kubernetes/hpa-function-invocation-per-second.yml"))
    run_command(f"kubectl apply -f kubernetes/hpa-function-invocation-per-second.yml")

    logger.info("SUT up and running.")
    logger.info(
        f"Run the following to benchmark: $ KUBE_CONTEXT=do-blr1-{cluster_name} "
        f'PROM_SERVER={prometheus} OUTPUT_DIR="results" '
        f"artillery run -t {gateway} load-generator/<test-definition>.yml"
    )


def list_clusters():
    run_command("doctl kubernetes cluster list --format ID,Name,Status")


def delete_cluster(cid: str):
    logger.info(f"Deleting cluster {cid}")
    run_command(f"doctl kubernetes cluster delete {cid} --dangerous")


def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(help="actions")
    function_map = {
        "create": create_cluster,
        "delete": delete_cluster,
        "list": list_clusters,
    }

    create_cluster_parser = subparsers.add_parser("create")
    create_cluster_parser.set_defaults(which="create")
    create_cluster_parser.add_argument("count", type=int, help="no. of worker nodes")
    create_cluster_parser.add_argument(
        "size",
        type=str,
        help="size of worker nodes",
        choices=["s-1vcpu-2gb", "s-2vcpu-2gb", "s-2vcpu-4gb", "s-4vcpu-8gb"],
    )
    create_cluster_parser.add_argument(
        "min_replicas", type=int, metavar="min-replicas", help="minimum no. of replicas"
    )
    create_cluster_parser.add_argument(
        "max_replicas", type=int, metavar="max-replicas", help="maximum no. of replicas"
    )
    create_cluster_parser.add_argument(
        "target_fips",
        type=float,
        metavar="target-fips",
        help="target average function invocations per second",
    )

    list_clusters_parser = subparsers.add_parser("list")
    list_clusters_parser.set_defaults(which="list")

    delete_cluster_parser = subparsers.add_parser("delete")
    delete_cluster_parser.set_defaults(which="delete")
    delete_cluster_parser.add_argument("cid", help="cluster id")

    args = parser.parse_args()
    args = vars(args)
    try:
        function_map[args.pop("which")](**args)
    except KeyError:
        parser.print_usage()


if __name__ == "__main__":
    main()
