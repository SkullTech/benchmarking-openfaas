import json
import os
import subprocess
import time
import uuid

DEFAULT_NUMBER = 10000019


def collect_metrics(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        container_id = str(uuid.uuid4())
        if os.path.exists("/tmp/container-id"):
            with open("/tmp/container-id", "r") as f:
                container_id = f.read()
        else:
            with open("/tmp/container-id", "w") as f:
                f.write(container_id)
        btime_line = subprocess.check_output("cat /proc/stat | grep btime", shell=True)
        host_btime = btime_line.decode().split()[1]

        output = func(*args, **kwargs)
        end_time = time.time()
        payload = {
            "metrics": {
                "executionStartTime": start_time,
                "executionEndTime": end_time,
                "executionLatency": end_time - start_time,
                "containerId": container_id,
                "hostId": host_btime,
            },
            "invocation": {
                "argument": int(args[0]) if args[0] else DEFAULT_NUMBER,
                "output": output == "True"
            }
        }
        return json.dumps(payload, indent=2)

    return wrapper


def if_prime(n):
    prime = [True for i in range(n + 1)]

    p = 2
    while p * p <= n:
        if prime[p]:
            for i in range(p * 2, n + 1, p):
                prime[i] = False
        p += 1
    prime[0] = False
    prime[1] = False

    return prime[-1]


@collect_metrics
def handle(req):
    number = int(req) if req else DEFAULT_NUMBER
    return str(if_prime(number))
