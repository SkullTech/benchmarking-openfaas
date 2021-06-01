import logging
import subprocess
import time
from argparse import ArgumentParser
from typing import Optional

import coloredlogs

logger = logging.getLogger()
coloredlogs.install(level="DEBUG", logger=logger)


def run_command(command: str, capture_output: bool = False) -> Optional[str]:
    logger.debug(f"Executing: {command}")
    cp = subprocess.run(command, shell=True, capture_output=capture_output)
    if capture_output:
        return cp.stdout.decode("UTF-8")


def create_cluster(size: str, count: int) -> None:
    logger.info(f"Creating cluster with {count} {size} nodes")
    cluster_name = f"{size}-{count}"
    run_command(
        "doctl kubernetes cluster create --1-clicks openfaas,metrics-server "
        f"--count {count} --region blr1 --size {size} {cluster_name}"
    )
    cluster_id = run_command(
        f"doctl kubernetes cluster get {cluster_name} --format ID --no-header",
        capture_output=True,
    ).strip()
    logger.info(f"Cluster created, name: {cluster_name}, ID: {cluster_id}")
    time.sleep(10)

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
    time.sleep(180)
    while True:
        output = run_command(
            "kubectl get service prometheus-external -n openfaas --no-headers",
            capture_output=True,
        )
        prometheus = f"http://{output.split()[3]}:9090"
        if "pending" not in prometheus:
            break
        time.sleep(10)
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
    )
    gateway = f"http://{output.split()[3]}:8080"
    logger.info(f"OpenFaaS gateway is available at: {gateway}")
    run_command(f"faas-cli login -g {gateway} -u admin -p {passwd}")

    logger.info("Deploying function to OpenFaaS")
    run_command(f"faas-cli deploy -f function/primality.yml --gateway {gateway}")


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
