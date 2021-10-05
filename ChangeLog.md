### 24/09/21

* Removed interceptors from main service as it is throwing "NoneType" exception for rpc_handler in context of grpc_interceptors lib but it works locally for some reason...

  The request validation can still be done via validator without the interceptors...

### 01/10/21

* Updated the service to use new protobufs messages

### 05/10/21

* Removed support for allowing for automatic provision of base images based on framework and python version. It needs the various m1l0 docker images to be completed first. At the moment, it takes a dockerfile argument