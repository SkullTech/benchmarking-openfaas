import json
from argparse import ArgumentParser

from fabric import Connection


def set_autoscaling_parameters(
    host: str,
    user: str,
    min_replicas: int,
    max_replicas: int,
    target_cpu_utilization_percentage: int,
):
    connection = Connection(host=host, user=user)
    patch_dict = {
        "spec": {
            "minReplicas": min_replicas,
            "maxReplicas": max_replicas,
            "targetCPUUtilizationPercentage": target_cpu_utilization_percentage,
        }
    }
    command = f"microk8s kubectl patch hpa pycon -n openfaas-fn --patch '{json.dumps(patch_dict)}'"
    result = connection.run(command, hide=True)
    print(result.stdout)


def main():
    parser = ArgumentParser()
    parser.add_argument("minReplicas", type=int)
    parser.add_argument("maxReplicas", type=int)
    parser.add_argument("targetCPUUtilizationPercentage", type=int)
    args = parser.parse_args()
    set_autoscaling_parameters(
        host="10.89.186.154",
        user="ubuntu",
        min_replicas=args.minReplicas,
        max_replicas=args.maxReplicas,
        target_cpu_utilization_percentage=args.targetCPUUtilizationPercentage,
    )


if __name__ == "__main__":
    main()
