## M1L0 Image Builder

gRPC service that packages and builds a ML project into a docker image for training

This component is part of a MLOPS pipeline project which is in development

It relies on the [m1l0-protobufs](https://github.com/m1l0ai/m1l0-protobufs)


### Call/invoking service locally

* Install the protobufs first:
  ```
  pip install m1l0-protobufs
  ```

* Create a set of TLS certificates as the service runs using secure connections:
  ```
  mkdir -p certs

  # Create a certs/server-ext.cnf file with the following:
  subjectAltName=DNS:localhost,DNS:builder,DNS:<domain name>,IP:0.0.0.0,IP:127.0.0.1

  # Replace the subj string in the Makefile command with the appropriate common name fields

  # Run certifcate generation command:
  make certificatesreq
  ```

* Create a .env file with the following:
  ```
  export MODE=Local
  export AWS_DEFAULT_REGION=<region name>
  export AWS_PROFILE=<profile name>
  export JOB_LOG_GROUP=<arn of cloudwatch log group>
  export M1L0_BUILDER_CA_PATH=/certs/ca-cert.pem
  export TF_VAR_DOCKERHUB_USER=<dockerhub user>
  export TF_VAR_DOCKERHUB_TOKEN=<dockerhub token>
  export TF_VAR_GITHUB_TOKEN=<github api token>
  ```

  The `MODE=Local` field means to run it locally.

  The `SECRET_NAME` refers to the AWS Secrets Manager entry defined in above step

  The `AWS_DEFAULT_PROFILE` and `AWS_PROFILE` are based on your local ~/.aws/config credentials

  
  The `JOB_LOG_GROUP` is a cloudwatch log group to store the job runs

  The `M1L0_BUILDER_CA_PATH` sets the ca cert path for the healthcheck service

  The `TF_VAR` variables set the service credentials required for both running the service locally and for deployment on AWS using terraform.


* Start the service:
  ```
  docker-compose up
  ```

* Check service is running:
  ```
  make host=builder check-service
  ```

  The `host=builder` refers to the service name since its running in a custom network

* Calling the service through gRPC client:
  ```python

  import uuid

  import grpc

  from m1l0_services.imagebuilder.v1.imagebuilder_service_pb2 import BuildRequest, BuildResponse, PushRequest, PushResponse, BuildTags, BuildIgnores, BuildConfig

  from m1l0_services.imagebuilder.v1.imagebuilder_service_pb2_grpc import ImageBuilderServiceStub

    host = os.environ.get("HOST", "localhost")
    
    cert_path = os.path.join(os.getcwd(), "certs")
    with open(os.path.join(cert_path, "ca-cert.pem"), "rb") as f:
        ca_cert = f.read()

    credentials = grpc.ssl_channel_credentials(
        root_certificates=ca_cert
    )
    channel = grpc.secure_channel(f"{host}:50051", credentials)
    client = ImageBuilderServiceStub(channel)

    config = {
        "service": "ecr",
        "repository": "target/myproject",
        "revision": "latest",
        "namespace": "myprojects",
        "name": "myproject",
        "dockerfile": "Dockerfile",
        "entry": "main.py",
        "tags": [{'Key': 'Project', 'Value': 'mnist'}, {'Key': 'Framework', 'Value': 'tensorflow-cpu-2.4.0'}],
        "source": "https://github.com/myrepo/myproject.git",
        "ignores": ['*.md', '*.npy', '.pytest_cache', '.gitignore', '.git', '__pycache__', '*.pyc', 'tmp*', 'checkpoints*', 'models*', 'backups', 'checkpoints', '*.tar.gz', "data"]
    }

    ignores = config.pop("ignores")
    tags = config.pop("tags")

    uid = str(uuid.uuid4())
    buildreq = BuildRequest(
        id=uid,
        config=BuildConfig(**config)
    )

    pushreq = PushRequest(
        id=uid,
        config=BuildConfig(**config)
    )

    # setup ignores
    for ig in ignores:
        ig2 = BuildIgnores(value=ig)
        buildreq.ignores.append(ig2)

    # setup tags
    for t in tags:
        tag = BuildTags(name=t["Key"], value=t["Value"])
        buildreq.tags.append(tag)
        pushreq.tags.append(tag)

    resp = client.Build(req)
    for r in resp:
        print(r.body)

    resp = client.Push(req2)
    for r in resp:
        print(r.body)
  ```

  The output will be streamed in the console.

  The logs are also stored in cloudwatch logs.

  The required fields are:

  * service

    must be either "dockerhub" or "ecr"

  * repository

    target to store image

  * source

    the source files / project to build image

    accepts "dir://<source>", "https://<github repo>.git", "s3://<bucket>/context.tar.gz"

    For "dir" builds, the source dir must be uploaded into the volume attached to the service and only works locally.

    For "git" builds, the client will attempt to clone the github repo

    For "s3" builds, the source must be packaged into a build context with a '.tar.gz' archive. Refer to the documentation below on build contexts.

  * dockerfile

    Name of dockerfile to use in source. Must be in path of source.

    This takes precedence

  * entry

    Name of file to set as ENTRYPOINT in image

  * tags

    List of tags to add to as labels to the image

  * ignores

    List of files to not include in the build.


### Building service

To build locally:
```
make build-localimage
```

To build and upload the image to ECR:
```
# set AWS_PROFILE, ECR_REPO
source .env.vars 

make build-remoteimage
```

To run the tests:
```
python setup.py test
```

### Deployment

The terraform scripts in the `terraform` directory allows you to deploy the service on ECS with the following resources:


* VPC with private and public subnets. The service is located in private subnet.

* EC2 Container instance running ECS AMI image which runs the service

* EC2 Instance running as bastion host in public subnet

* Keypair for SSH access

* IAM policies

* Application Load Balancer with target group with gRPC protocol

* Certificate Manager for private and CA certs

* Secrets manager entries for docker and github services

To deploy:
```
source .env

make setup
```

To teardown:
```
make teardown
```

### Notes on Docker build context

To create a build context as a 'tar.gz' archive, need to add the source as a flat directory into the archive:

```
tar -czvf context.tar.gz -C <project source> .

cat context.tar.gz | docker build -  -t myimg:latest
```

### TODO:

* Setting up metadata store to store records of build artifacts