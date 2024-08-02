package main

import (
	"log"
	"os"

	"github.com/go-openapi/loads"
	flags "github.com/jessevdk/go-flags"

	"asb-queue-emulator/config"
	"asb-queue-emulator/pkg/broker/brokerutils"
	"asb-queue-emulator/swagger/gen/restapi"
	"asb-queue-emulator/swagger/gen/restapi/operations"
	"asb-queue-emulator/swagger/utils"
)

// This file was generated by the swagger tool.
// Make sure not to overwrite this file after you generated it because all your edits would be lost!

func main() {
	if err := config.ImportConfig(); err != nil {
		log.Fatalln(err)
	}

	swaggerSpec, err := loads.Embedded(restapi.SwaggerJSON, restapi.FlatSwaggerJSON)
	if err != nil {
		log.Fatalln(err)
	}

	serverPort := brokerutils.GetServerPort()

	broker, err := brokerutils.GetBroker()
	if err != nil {
		log.Fatalln(err)
	}

	if err := brokerutils.CreateQueues(broker); err != nil {
		log.Fatalln(err)
	}

	restapi.AzureServiceBusAPIContext = utils.HandlerContext{
		MQBroker: broker,
	}

	api := operations.NewAzureServiceBusAPI(swaggerSpec)
	server := restapi.NewServer(api)
	server.Port = serverPort
	defer server.Shutdown()

	parser := flags.NewParser(server, flags.Default|flags.IgnoreUnknown)

	if _, err := parser.Parse(); err != nil {
		code := 1
		if fe, ok := err.(*flags.Error); ok {
			if fe.Type == flags.ErrHelp {
				code = 0
			}
		}
		os.Exit(code)
	}

	server.ConfigureAPI()

	if err := server.Serve(); err != nil {
		log.Fatalln(err)
	}
}
