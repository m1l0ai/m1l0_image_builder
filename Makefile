.PHONY: build-protobufs remove-volumes dist build-image

build-protobufs:
	python -m grpc_tools.protoc -I protobufs --python_out=gprotobufs --grpc_python_out=gprotobufs protobufs/image_builder.proto

build-image:
	docker build --force-rm -t m1l0/builder:latest -f Dockerfile .

run-service:
	PYTHONPATH="${PWD}/gprotobufs" \
	python builder/service.py

run-client:
	 PYTHONPATH="${PWD}/gprotobufs:${PWD}/builder" \
	 python testpackage.py 

remove-volumes:
	docker volume ls --filter label=m1l0.job-id --format "{{.Name}}" | xargs -r docker volume rm

dist:
	python setup.py bdist_wheel

clean:
	rm -rf build dist *.egg-info .eggs .coverage .pytest* htmlcov