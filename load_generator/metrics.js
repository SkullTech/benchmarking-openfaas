const csv = require("fast-csv")
const fs = require("fs")
const {
    v4: uuidv4,
} = require('uuid');

module.exports = {
    beforeRequest: beforeRequest,
    afterResponse: afterResponse
};


const csvStream = csv.format({headers: true});
let writableStream = fs.createWriteStream(`result-${Date.now()}.csv`, {flags: 'a'});
csvStream.pipe(writableStream);


function beforeRequest(requestParams, context, ee, next) {
    context.startTime = Date.now() / 1000
    context.requestId = uuidv4();
    return next(); // MUST be called for the scenario to continue
}

function afterResponse(requestParams, response, context, ee, next) {
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
    if (response.statusCode < 300) {
        metrics.schedulingLatency = metrics["executionStartTime"] - metrics.requestTime;
    }
    csvStream.write(metrics);
    return next(); // MUST be called for the scenario to continue
}
