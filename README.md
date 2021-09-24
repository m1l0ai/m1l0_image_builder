### M1L0 Image Builder

gRPC service that packages and builds a ML Project into a docker image

This component is part of a larger pipeline project which is in development


### Call/invoking service

The config object to pass to the request can be a dict or even parsed from YAML but it needs a basic structure as follows:
```
config = {
        "service": "ecr",
        "repository": "target/myproject",
        "revision": "latest",
        "namespace": "cheeprojects",
        "name": "myproject",
        "framework": "tensorflow",
        "version": "2.6.0",
        "pyversion": "3.6",
        "resource": "cpu",
        "entry": "main.py",
        "tags": [{'Key': 'Project', 'Value': 'mnist'}, {'Key': 'Framework', 'Value': 'tensorflow-cpu-2.4.0'}],
        "source": "https://github.com/myrepo/myproject.git",
        "ignores": ['*.md', '*.npy', '.pytest_cache', '.gitignore', '.git', '__pycache__', '*.pyc', 'tmp*', 'checkpoints*', 'models*', 'backups', 'checkpoints', '*.tar.gz', "data"]
    }
```

The fields are explained as below:

* service

  The service to use to deploy the final image to. Can only be one of "dockerhub" or "ecr"

* repository

  The target repository to deploy the final image to. For dockerhub need to only specify the repository as "<user>/<project>". For ecr, need to specify only the last portion of the ecr url which can be either "<user>/<project>" or "<project"> 

* revision
	
	Version of the image you're building


The following fields are required:
* service
* repository
* source



An example request as follows using the gRPC client:
```


```

### Building service

To build locally:
```
source .env.vars

make build-image
```

To run server:
```
make run-service

```

To run test client locally:
```
make run-client
```

### Docker build context

Running custom dockerfile

Need to archive dir into flat directory:
```
tar -czvf files.tar.gz -C ../mnist_example .

cat files.tar.gz | docker build -  -t myimg:latest
```

above ^ means to cd into ../mnist_example and 