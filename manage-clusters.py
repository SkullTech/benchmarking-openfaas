import logging
import subprocess
from argparse import ArgumentParser

import coloredlogs

logger = logging.getLogger()
coloredlogs.install(level="DEBUG", logger=logger)


def create_cluster(size: str, count: int, dry: bool = False):
    command = f"doctl kubernetes cluster create --1-clicks openfaas,metrics-server --count {count} --region blr1 --size {size} {size}-{count}"
    logger.info(f"Creating cluster with {count} {size} nodes")
    logger.debug(f"Executing: {command}")
    if not dry:
        subprocess.run(command, shell=True)

    command = 'echo $(kubectl -n openfaas get secret basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode)'
    logger.info("Fetching OpenFaaS password")
    logger.debug(f"Executing: {command}")
    if not dry:
        passwd = subprocess.run(command, shell=True)
        logger.info(f"OpenFaaS password is: {passwd}")

    command = "helm install prometheus-adapter prometheus-community/prometheus-adapter -f kubernetes/values-prometheus-adapter.yml"
    logger.info(f"Installing prometheus-adapter on cluster")
    logger.debug(f"Executing: {command}")
    if not dry:
        subprocess.run(command, shell=True)


def list_clusters(dry: bool = False):
    command = f"doctl kubernetes cluster list --format ID,Name,Status"
    logger.debug(f"Executing: {command}")
    if not dry:
        subprocess.run(command, shell=True)


def delete_cluster(cid: str, dry: bool = False):
    command = f"doctl kubernetes cluster delete {cid} --dangerous"
    logger.info(f"Deleting cluster {cid}")
    logger.debug(f"Executing: {command}")
    if not dry:
        subprocess.run(command, shell=True)


def main():
    parser = ArgumentParser()
    parser.add_argument("--dry", help="dry run", action="store_true")
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
