.PHONY: build-protobufs remove-volumes dist build-image

build-protobufs:
	python -m grpc_tools.protoc -I protobufs --python_out=gprotobufs --grpc_python_out=gprotobufs protobufs/image_builder.proto

build-image:
	docker build --force-rm -t m1l0/builder:latest -f Dockerfile .

run-service:
	python main.py

run-client:
	 python testpackage.py

run-tests:
	python setup.py test

check-service:
	docker run --rm --network m1l0net fullstorydev/grpcurl:latest --plaintext builder:50051 list

	docker run --rm --network m1l0net fullstorydev/grpcurl:latest --plaintext -d '{"service": ""}' builder:50051 grpc.health.v1.Health/Check

	docker run --rm --network m1l0net fullstorydev/grpcurl:latest --plaintext -d '{"service": "grpc.m1l0_services.imagebuilder.ImageBuilder"}' builder:50051 grpc.health.v1.Health/Check

remove-volumes:
	docker volume ls --filter label=m1l0.job-id --format "{{.Name}}" | xargs -r docker volume rm

dist:
	python setup.py bdist_wheel

clean:
	rm -rf build dist *.egg-info .eggs .coverage .pytest* htmlcov