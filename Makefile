.PHONY: build-protobufs remove-volumes dist

build-protobufs:
	python -m grpc_tools.protoc -I protobufs --python_out=gprotobufs --grpc_python_out=gprotobufs protobufs/image_builder.proto

run-service:
	PYTHONPATH="${PWD}/gprotobufs" \
	python service.py

run-client:
	 PYTHONPATH="${PWD}/gprotobufs" \
	 python testpackage.py 

remove-volumes:
	docker volume ls --filter label=m1l0.job-id --format "{{.Name}}" | xargs -r docker volume rm

dist:
	python setup.py bdist_wheel

clean:
	rm -rf build dist *.egg-info .eggs .coverage .pytest* htmlcov