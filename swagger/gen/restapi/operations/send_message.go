// Code generated by go-swagger; DO NOT EDIT.

package operations

// This file was generated by the swagger tool.
// Editing this file might prove futile when you re-run the generate command

import (
	"net/http"

	"github.com/go-openapi/runtime/middleware"
)

// SendMessageHandlerFunc turns a function with the right signature into a send message handler
type SendMessageHandlerFunc func(SendMessageParams) middleware.Responder

// Handle executing the request and returning a response
func (fn SendMessageHandlerFunc) Handle(params SendMessageParams) middleware.Responder {
	return fn(params)
}

// SendMessageHandler interface for that can handle valid send message params
type SendMessageHandler interface {
	Handle(SendMessageParams) middleware.Responder
}

// NewSendMessage creates a new http.Handler for the send message operation
func NewSendMessage(ctx *middleware.Context, handler SendMessageHandler) *SendMessage {
	return &SendMessage{Context: ctx, Handler: handler}
}

/* SendMessage swagger:route POST /{queueName}/messages sendMessage

SendMessage send message API

*/
type SendMessage struct {
	Context *middleware.Context
	Handler SendMessageHandler
}

func (o *SendMessage) ServeHTTP(rw http.ResponseWriter, r *http.Request) {
	route, rCtx, _ := o.Context.RouteInfo(r)
	if rCtx != nil {
		r = rCtx
	}
	var Params = NewSendMessageParams()
	if err := o.Context.BindValidRequest(r, route, &Params); err != nil { // bind params
		o.Context.Respond(rw, r, route.Produces, route, err)
		return
	}

	res := o.Handler.Handle(Params) // actually handle the request
	o.Context.Respond(rw, r, route.Produces, route, res)

}
