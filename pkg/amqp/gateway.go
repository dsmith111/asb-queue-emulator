package amqp

import (
	"bytes"
	"encoding/json"
	"io/ioutil"
	"net/http"
	"time"

	amqp "github.com/Azure/go-amqp"
)

// TODO Get definition from Swagger
var sendMessageMethod = http.MethodPut
var sendMessageUrl = "/test"

/*
** Converts an AMQP Message to an HTTP Request as expected by ServiceBus API
 */
func AmqpToHttp(amqpMessage *amqp.Message) (*http.Request, error) {

	// Amqp Properties and Header go into BrokerProperties Header
	// Example:
	// BrokerProperties: {"Label":"M1","State":"Active","TimeToLive":10}
	// Priority: High
	// Customer: 12345,ABC

	headerJson, err := json.Marshal(amqpMessage.Header)
	propJson, err := json.Marshal(amqpMessage.Properties)

	// Both Header and Properties need to be combined into one HTTP Header
	out := map[string]interface{}{}
	json.Unmarshal([]byte(headerJson), &out)
	json.Unmarshal([]byte(propJson), &out)
	BrokerPropertiesJson, _ := json.Marshal(out)

	// Message Data / Body
	ampqData := amqpMessage.GetData()
	body := bytes.NewBuffer(ampqData)

	method := sendMessageMethod
	url := sendMessageUrl

	// Build HTTP Request
	httpMessage, err := http.NewRequest(method, url, body)
	if err != nil {
		return nil, err
	}

	httpMessage.Header.Add("BrokerProperties", string(BrokerPropertiesJson))

	return httpMessage, nil
}

// If a batch of messages is sent, these properties are part of the JSON-encoded HTTP body. For more information, see Send Message and Send Message Batch.
// Reference: https://learn.microsoft.com/en-us/rest/api/servicebus/message-headers-and-properties
func AmqpToHttpBatch(amqpMessage *amqp.Message) (*http.Request, error) {
	if amqpMessage == nil {
		return http.NewRequest(sendMessageMethod, sendMessageUrl, bytes.NewReader([]byte{}))
	}

	headerJSON, _ := json.Marshal(amqpMessage.Header)
	propJSON, _ := json.Marshal(amqpMessage.Properties)

	props := map[string]interface{}{}
	if err := json.Unmarshal(headerJSON, &props); err != nil {
		return nil, err
	}
	if err := json.Unmarshal(propJSON, &props); err != nil {
		return nil, err
	}

	bodyMap := map[string]interface{}{
		"Body":             string(amqpMessage.GetData()),
		"BrokerProperties": props,
	}

	if amqpMessage.ApplicationProperties != nil {
		app := map[string]interface{}{}
		for k, v := range amqpMessage.ApplicationProperties {
			app[k] = v
		}
		if len(app) > 0 {
			bodyMap["Properties"] = app
		}
	}

	payload, err := json.Marshal([]map[string]interface{}{bodyMap})
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest(sendMessageMethod, sendMessageUrl, bytes.NewBuffer(payload))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")
	return req, nil
}

/*
** Converts a HTTP Response to an AMPQ Message
 */
func HttpToAmqp(httpResponse *http.Response) (*amqp.Message, error) {
	responseBody := httpResponse.Body
	body, err := ioutil.ReadAll(responseBody)
	if err != nil {
		return nil, err
	}

	amqpMessage := amqp.NewMessage(body)

	brokerProps := httpResponse.Header.Get("BrokerProperties")
	if brokerProps != "" {
		var props map[string]interface{}
		if err := json.Unmarshal([]byte(brokerProps), &props); err == nil {
			header := &amqp.MessageHeader{}
			if v, ok := props["Durable"].(bool); ok {
				header.Durable = v
			}
			if v, ok := props["Priority"].(float64); ok {
				header.Priority = uint8(v)
			}
			if v, ok := props["TTL"].(float64); ok {
				header.TTL = time.Duration(v)
			}
			if v, ok := props["FirstAcquirer"].(bool); ok {
				header.FirstAcquirer = v
			}
			if v, ok := props["DeliveryCount"].(float64); ok {
				header.DeliveryCount = uint32(v)
			}

			amqpMessage.Header = header

			properties := &amqp.MessageProperties{}
			if v, ok := props["MessageId"]; ok {
				properties.MessageID = v
			}
			if v, ok := props["CorrelationId"]; ok {
				properties.CorrelationID = v
			}
			if v, ok := props["To"].(string); ok {
				properties.To = &v
			}
			if v, ok := props["ReplyTo"].(string); ok {
				properties.ReplyTo = &v
			}
			if v, ok := props["Subject"].(string); ok {
				properties.Subject = &v
			}
			if v, ok := props["ContentType"].(string); ok {
				properties.ContentType = &v
			}
			if v, ok := props["ReplyToGroupID"].(string); ok {
				properties.ReplyToGroupID = &v
			}
			if v, ok := props["GroupID"].(string); ok {
				properties.GroupID = &v
			}
			if v, ok := props["GroupSequence"].(float64); ok {
				seq := uint32(v)
				properties.GroupSequence = &seq
			}

			amqpMessage.Properties = properties
		}
	}

	appProps := map[string]interface{}{}
	for k, v := range httpResponse.Header {
		if k == "BrokerProperties" || k == "Content-Type" {
			continue
		}
		if len(v) > 0 {
			appProps[k] = v[len(v)-1]
		}
	}
	if len(appProps) > 0 {
		amqpMessage.ApplicationProperties = appProps
	}

	return amqpMessage, nil
}
