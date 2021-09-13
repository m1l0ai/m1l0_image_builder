### M1L0 Image Builder

Builds a ML Project given some config such as directory path, root file etc

To build image:
```
source .env.vars

make build-image

```


To run server:
```
make run-service

```

To run test client locally:
```python
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