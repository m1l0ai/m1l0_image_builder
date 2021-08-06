### M1L0 Image Builder

Builds a ML Project given some config such as directory path, root file etc

More details to come ...


To run test client:
```python


 PYTHONPATH="${PWD}/gprotobufs" python testpackage.py 
 
```

### TODO:

* Healthcheck for grpc service

  Example implementation here:
  https://github.com/grpc/grpc/tree/master/examples/python/xds

* Use grpc interceptors to return appropriate errors...

  Useful to use interceptors for request params validation

* Change to using buildah for the builds ?? Install and package buildah with the service image ???

* Move protobufs into its own package and reimport it here...