### TODO:

* Refactor the code retrieval to add more formats

  core/retriever.py


* Healthcheck for grpc service

  https://stackoverflow.com/questions/56984565/python-grpc-health-check

  Example implementation here:
  https://github.com/grpc/grpc/tree/master/examples/python/xds


* To test using grpcurl:
  ```
  docker run --rm --network m1l0net fullstorydev/grpcurl:latest --plaintext builder:50051 list


  docker run --rm --network m1l0net fullstorydev/grpcurl:latest --plaintext -d '{"service": "protobufs.m1l0_services.imagebuilder.ImageBuilder"}' builder:50051 grpc.health.v1.Health/Check

  => should return {"status": "Serving"} if running

  docker run --rm --network m1l0net fullstorydev/grpcurl:latest --plaintext -d '{"service": ""}' builder:50051 grpc.health.v1.Health/Check

  => should return {"status": "Serving"} if running
  
  ```

  How do we use the grpcurl as HEALTHCHECK in Dockerfile?

  use: https://github.com/grpc-ecosystem/grpc-health-probe/

  https://medium.com/geekculture/implementing-healthchecks-in-grpc-containers-for-kubernetes-d5049989ab12


* Use grpc interceptors to return appropriate errors...

  Useful to use interceptors for request params validation

* Change to using buildah for the builds ?? Install and package buildah with the service image ???



https://stackoverflow.com/questions/44077407/is-there-a-way-to-automatically-activate-a-virtualenv-as-a-docker-entrypoint