const csv = require("fast-csv")
const fs = require("fs")
const {
    v4: uuidv4,
} = require('uuid');
const axios = require('axios').default;
const k8s = require('@kubernetes/client-node');
const request = require('request-promise-native');

module.exports = {
    beforeRequest: beforeRequest,
    afterResponse: afterResponse
};

const csvStream = csv.format({headers: true});
let writableStream = fs.createWriteStream(`result-${Date.now()}.csv`, {flags: 'a'});
csvStream.pipe(writableStream);

const kc = new k8s.KubeConfig();
kc.loadFromDefault();
const opts = {};
kc.applyToRequest(opts);
const kubeServer = kc.getCurrentCluster().server;


function beforeRequest(requestParams, context, ee, next) {
    context.startTime = Date.now() / 1000
    context.requestId = uuidv4();
    return next(); // MUST be called for the scenario to continue
}

async function afterResponse(requestParams, response, context, ee, next) {
    let metrics = {}
    if (response.statusCode < 300) {
        metrics = JSON.parse(response.body)["metrics"];
        metrics.statusCode = response.statusCode
    } else {
        metrics.statusCode = response.statusCode
    }
    metrics.requestResponseLatency = (Date.now() / 1000) - context.startTime;
    metrics.requestTime = context.startTime
    metrics.responseTime = Date.now() / 1000
    metrics.requestId = context.requestId

    try {
        let promResponse = await axios.get(
            "http://10.89.186.87:9090/api/v1/query", {
                params: {
                    query: 'count(count by (kubernetes_pod_name) (up{faas_function="pycon"}))'
                }
            }
        );
        metrics.replicas = promResponse.data.data.result[0].value[1];
    } catch (err) {}

    try {
        let nodeMetrics = JSON.parse(await request.get(`${kubeServer}/apis/metrics.k8s.io/v1beta1/nodes`, opts))
        for (const item of nodeMetrics.items) {
            metrics[`${item.metadata.name}CpuUsage`] = item.usage.cpu;
            metrics[`${item.metadata.name}MemoryUsage`] = item.usage.memory;
        }
    } catch (err) {}

    try {
        let invocationMetrics = JSON.parse(await request.get(`${kubeServer}/apis/external.metrics.k8s.io/v1beta1/namespaces/openfaas-fn/gateway_function_invocation_per_second`, opts))
        metrics.functionInvocationRate = invocationMetrics.items[0].value;
    } catch (err) {}

    if (response.statusCode < 300) {
        metrics.schedulingLatency = metrics["executionStartTime"] - metrics.requestTime;
    }

    csvStream.write(metrics);
    return next(); // MUST be called for the scenario to continue
}
