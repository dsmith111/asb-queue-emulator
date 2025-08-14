from  proton import Message
import http.client
import requests
import json

# Constants for read/write types (i.e. peek lock, receive and delete, store)
PEEK = "PEEK"
WRITE = "WRITE"
READ = "READ"

# This needs to be the same as the HTTP server's port
CONFIGURED_PORT = 4444

# Receives a Amqp Message and sends it to the http server and then parses the response back to http
def HandleAmqpMessage(queue_name: str, amqpMessage: Message, operation_type: str) -> Message:
    # Build the http address from the queue name http://localhost:<CONFIGURED_PORT>/<queue_name>
    destination_address = "http://asbemulator:" + str(CONFIGURED_PORT) + "/" + queue_name
    formattedPath, method = FormatHTTPOperation(operation_type, destination_address)

    print("Converting AMQP message to HTTP request.")
    httpRequest = AmqpToHttp(formattedPath, amqpMessage, method)
    print("HTTP request: ", httpRequest)
    preparedRequest = httpRequest.prepare()
    session = requests.Session()

    print("Sending HTTP request.")
    httpResponse = session.send(preparedRequest)

    if operation_type == PEEK or operation_type == READ:
        # TODO handle / parse the response
        amqpResponse = HttpToAmqp(httpResponse)
        return amqpResponse
    
    return None


# Translates an AMQP message to an HTTP Request
def AmqpToHttp(path: str, amqpMessage: Message, method: str):
    if amqpMessage is None:
        return requests.Request(
            method = method,
            url = path
        )
    
    brokerPropJson = dict()

    # Properties on the Message Object
    brokerPropJson["ContentType"] = amqpMessage.content_type
    brokerPropJson["CorrelationId"] = amqpMessage.correlation_id
    brokerPropJson["DeliveryCount"] = amqpMessage.delivery_count
    brokerPropJson["ExpiresAtUtc"] = amqpMessage.expiry_time
    brokerPropJson["Label"] = amqpMessage.subject
    brokerPropJson["MessageId"] = amqpMessage.id
    brokerPropJson["ReplyTo"] = amqpMessage.reply_to
    brokerPropJson["ReplyToSessionId"] = amqpMessage.reply_to_group_id 
    brokerPropJson["SessionId"] = amqpMessage.group_id
    brokerPropJson["TimeToLive"] = amqpMessage.ttl
    brokerPropJson["To"] = amqpMessage.address # No 'to' found

    # Message Annotations
    # Reference: https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-amqp-protocol-guide#message-annotations
    if amqpMessage.annotations is not None and isinstance(amqpMessage.annotations, dict):
        brokerPropJson["ScheduledEnqueueTimeUtc"] = amqpMessage.annotations.get("x-opt-scheduled-enqueue-time")
        brokerPropJson["PartitionKey"] = amqpMessage.annotations.get("x-opt-partition-key")
        brokerPropJson["ViaPartitionKey"] = amqpMessage.annotations.get("x-opt-via-partition-key")
        brokerPropJson["EnqueuedTimeUtc"] = amqpMessage.annotations.get("x-opt-enqueued-time")
        brokerPropJson["SequenceNumber"] = amqpMessage.annotations.get("x-opt-sequence-number")
        brokerPropJson["EnqueueSequenceNumber"] = amqpMessage.annotations.get("x-opt-offset")
        brokerPropJson["LockedUntilUtc"] = amqpMessage.annotations.get("x-opt-locked-until")
        brokerPropJson["DeadLetterSource"] = amqpMessage.annotations.get("x-opt-deadletter-source")
 
    # The body is a memoryview. We need to decode it
    payload = amqpMessage.body
    if type(payload) is memoryview:
        payload = payload.tobytes()
    if type(payload) is bytes:
        payload = payload.decode("utf-8")
    formatted_payload = {
        "content": payload,
    }
    formatted_payload = json.dumps(formatted_payload)
    
    # Build the Request, don't send it yet
    httpRequest = requests.Request(
        method = method,
        url = path,
        data = formatted_payload
    )
    httpRequest.headers["BrokerProperties"] = json.dumps(brokerPropJson) or ""
    httpRequest.headers["Content-Type"] = "application/json"

    # Set custom user properties
    # If a single message is sent or received, each custom property is placed in its own HTTP header.
    if amqpMessage.properties is not None and isinstance(amqpMessage.properties, dict):
        for key, value in amqpMessage.properties.items():
            httpRequest.headers[key] = value

    return httpRequest

def HttpToAmqp(httpResponse: http.client.HTTPResponse) -> Message:
    body = httpResponse.content
    if isinstance(body, bytes):
        payload = body.decode("utf-8")
    else:
        payload = body

    response = Message()
    response.body = payload
    response.correlation_id = httpResponse.headers.get("CorrelationId", 0)

    broker_header = httpResponse.headers.get("BrokerProperties")
    if broker_header:
        try:
            props = json.loads(broker_header)
        except Exception:
            props = {}

        response.id = props.get("MessageID") or props.get("MessageId")
        response.reply_to = props.get("ReplyTo")
        response.ttl = props.get("TTL") or props.get("TimeToLive", 0)
        response.delivery_count = props.get("DeliveryCount", 0)
        response.address = props.get("To")
        response.subject = props.get("Label") or props.get("Subject")

    app_props = {}
    for k, v in httpResponse.headers.items():
        if k.lower() in ["brokerproperties", "content-type"]:
            continue
        app_props[k] = v

    if app_props:
        response.properties = app_props

    return response

def FormatHTTPOperation(operation_type: str, path: str):
    method = ""
    if operation_type == PEEK:
        path = join_url(path, "/messages/head")
        method = "POST"
    elif operation_type == WRITE:
        path = join_url(path, "/messages")
        method = "POST"
    elif operation_type == READ:
        path = join_url(path, "/messages/head")
        method = "DELETE"
    return path, method

def join_url(base_url, relative_path):
    return base_url.rstrip('/') + '/' + relative_path.lstrip('/')
