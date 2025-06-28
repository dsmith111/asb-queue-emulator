import unittest
from  proton import Message
import requests
import json

from . import amqp_translator

class TestAmqpTranslation(unittest.TestCase):
    # Basic test to validate body and headers are set
    def test_amqpToHttp(self):

        path = "https://test"
        payload = memoryview(bytearray("This is a test body.", "UTF-8"))
        messageTest = Message(
            body=payload,
            content_type = "",
            correlation_id = "1234",
            delivery_count = 0,
            expiry_time = 0, #"0001-01-01T00:00:00Z",
            subject = "",
            id = "cc710747-df0a-46f8-9959-1f8b0d55eb42",
            reply_to = "",
            reply_to_group_id = "",
            group_id = "",
            ttl = 0, # "",
            address = "",
        )

        messageTest.annotations = dict()
        messageTest.annotations["x-opt-scheduled-enqueue-time"] = 0
        messageTest.annotations["x-opt-partition-key"] = ""
        messageTest.annotations["x-opt-via-partition-key"] = ""
        messageTest.annotations["x-opt-enqueued-time"] = "0001-01-01T00:00:00Z"
        messageTest.annotations["x-opt-sequence-number"] = 0
        messageTest.annotations["x-opt-offset"] = 0
        messageTest.annotations["x-opt-locked-until"] = "0001-01-01T00:00:00Z"
        messageTest.annotations["x-opt-deadletter-source"] = ""

        messageTest.properties = dict()
        messageTest.properties["CustomOperationName"] = "mockOperation"
        messageTest.properties["CustomOperationId"] = "abc"

        expectedBrokerPropJson = dict()
        # Properties on the Message Object 
        expectedBrokerPropJson["ContentType"] = ""
        expectedBrokerPropJson["CorrelationId"] = "1234"
        expectedBrokerPropJson["DeliveryCount"] = 0
        expectedBrokerPropJson["ExpiresAtUtc"] = 0
        expectedBrokerPropJson["Label"] = ""
        expectedBrokerPropJson["MessageId"] = "cc710747-df0a-46f8-9959-1f8b0d55eb42"
        expectedBrokerPropJson["ReplyTo"] = ""
        expectedBrokerPropJson["ReplyToSessionId"] = ""
        expectedBrokerPropJson["SessionId"] = ""
        expectedBrokerPropJson["TimeToLive"] = 0
        expectedBrokerPropJson["To"] = ""

        # Message Annotations
        expectedBrokerPropJson["ScheduledEnqueueTimeUtc"] = 0
        expectedBrokerPropJson["PartitionKey"] = ""
        expectedBrokerPropJson["ViaPartitionKey"] = ""
        expectedBrokerPropJson["EnqueuedTimeUtc"] = "0001-01-01T00:00:00Z"
        expectedBrokerPropJson["SequenceNumber"] = 0
        expectedBrokerPropJson["EnqueueSequenceNumber"] = 0
        expectedBrokerPropJson["LockedUntilUtc"] = "0001-01-01T00:00:00Z"
        expectedBrokerPropJson["DeadLetterSource"] = ""

        constructedHttpRequest = amqp_translator.AmqpToHttp(path, messageTest, "POST")
 
        brokerPropJson = json.loads(constructedHttpRequest.headers["BrokerProperties"])

        # Validate each of the expected headers is set
        for k,v in expectedBrokerPropJson.items():
            self.assertTrue(k in brokerPropJson, "Expected key {k} not found in BrokerProperties HTTP Header".format(k=k))
            self.assertEqual(v, brokerPropJson[k], "BrokerProperties HTTP Header key {k} does not have expected value {expectedvalue}, received value {value}".format(k=k,expectedvalue=v, value=brokerPropJson[k]))

        # Validate custom headers
        self.assertTrue("CustomOperationName" in constructedHttpRequest.headers, "Missing custom header in HTTP Header")
        self.assertEqual("mockOperation", constructedHttpRequest.headers["CustomOperationName"], "Custom header has incorrect value.")

        self.assertTrue("CustomOperationId" in constructedHttpRequest.headers, "Missing custom header in HTTP Header")
        self.assertEqual("abc", constructedHttpRequest.headers["CustomOperationId"], "Custom header has incorrect value.")

        self.assertEqual( constructedHttpRequest.data, '{"content": "This is a test body."}')

    def test_httpToAmqp(self):
        resp = requests.Response()
        resp._content = b"hello"
        resp.status_code = 201
        resp.headers["BrokerProperties"] = json.dumps({"MessageId": "1", "CorrelationId": "abc", "DeliveryCount": 2})
        resp.headers["CustomKey"] = "Value"

        message = amqp_translator.HttpToAmqp(resp)

        self.assertEqual(message.body, "hello")
        self.assertEqual(message.id, "1")
        self.assertEqual(message.correlation_id, resp.headers.get("CorrelationId", 0))
        self.assertEqual(message.delivery_count, 2)
        self.assertIn("CustomKey", message.properties)
        self.assertEqual(message.properties["CustomKey"], "Value")

if __name__ == '__main__':
    unittest.main()
