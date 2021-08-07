### M1L0 Image Builder

Builds a ML Project given some config such as directory path, root file etc

More details to come ...


To run test client:
```python


 PYTHONPATH="${PWD}/gprotobufs" python testpackage.py 
 
```

### TODO:

* Healthcheck for grpc service


  https://stackoverflow.com/questions/56984565/python-grpc-health-check

  Example implementation here:
  https://github.com/grpc/grpc/tree/master/examples/python/xds


  To test using grpcurl:
  ```
  docker run --rm --network m1l0net fullstorydev/grpcurl:latest --plaintext builder:50051 list


  docker run --rm --network m1l0net fullstorydev/grpcurl:latest --plaintext -d '{"service": "ImageBuilder"}' builder:50051 grpc.health.v1.Health/Check

  => should return {"status": "Serving"} if running

  docker run --rm --network m1l0net fullstorydev/grpcurl:latest --plaintext -d '{"service": ""}' builder:50051 grpc.health.v1.Health/Check

  => should return {"status": "Serving"} if running
  
  ```

  How do we use the grpcurl as HEALTHCHECK in Dockerfile?

  use: https://github.com/grpc-ecosystem/grpc-health-probe/
  
  https://medium.com/geekculture/implementing-healthchecks-in-grpc-containers-for-kubernetes-d5049989ab12



* Move protobufs into its own package and reimport it here...


* Use grpc interceptors to return appropriate errors...

  Useful to use interceptors for request params validation

* Change to using buildah for the builds ?? Install and package buildah with the service image ???