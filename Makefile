.PHONY: build-protobufs remove-volumes dist build-image create-secrets certificates certificates2

create-secrets:
	aws --profile devs secretsmanager create-secret --name m1l0/creds --secret-string file://ssm.json

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

# Disable TLS Verification due to self-signed certs
# https://github.com/fullstorydev/grpcurl/issues/90
check-service:
	docker run -v "${PWD}/certs":/tmp/certs --rm --network m1l0net fullstorydev/grpcurl:latest -cacert=/tmp/certs/ca-cert.pem builder:50051 describe

	docker run -v "${PWD}/certs":/tmp/certs --rm --network m1l0net fullstorydev/grpcurl:latest -cacert=/tmp/certs/ca-cert.pem builder:50051 list

	docker run -v "${PWD}/certs":/tmp/certs --rm --network m1l0net fullstorydev/grpcurl:latest -cacert=/tmp/certs/ca-cert.pem  builder:50051 grpc.health.v1.Health/Check

	docker run -v "${PWD}/certs":/tmp/certs --rm --network m1l0net fullstorydev/grpcurl:latest -cacert=/tmp/certs/ca-cert.pem -d '{"service": "grpc.m1l0_services.imagebuilder.ImageBuilder"}' builder:50051 grpc.health.v1.Health/Check

remove-volumes:
	docker volume ls --filter label=m1l0.job-id --format "{{.Name}}" | xargs -r docker volume rm

remove:
	pip uninstall -y m1l0-builder

dist:
	python setup.py bdist_wheel

clean:
	rm -rf build dist *.egg-info .eggs .coverage .pytest* htmlcov

certificates:
	openssl genrsa -out certs/server.key 2048

	openssl req -nodes -new -x509 -sha256 -days 1825 -config certificate.conf -extensions 'req_ext' -key certs/server.key -out certs/server.crt


certificates2:
	rm -rf certs/*.pem

	# 1. Generate CA's private key and self-signed certificate
	openssl req -x509 -newkey rsa:4096 -days 365 -nodes -keyout certs/ca-key.pem -out certs/ca-cert.pem -subj "/C=UK/ST=UK/L=UK/O=M1L0/CN=*.m1l0.xyz/emailAddress=ca@example.com"

	echo "CA's self-signed certificate"
	openssl x509 -in certs/ca-cert.pem -noout -text

	# 2. Generate web server's private key and certificate signing request (CSR)

	openssl req -newkey rsa:4096 -nodes -keyout certs/server-key.pem -out certs/server-req.pem -subj "/C=UK/ST=UK/L=UK/O=M1L0 Builder/CN=localhost/emailAddress=example@example.com"

	# 3. Use CA's private key to sign web server's CSR and get back the signed certificate
	openssl x509 -req -in certs/server-req.pem -days 60 -CA certs/ca-cert.pem -CAkey certs/ca-key.pem -CAcreateserial -out certs/server-cert.pem -extfile certs/server-ext.cnf

	echo "Server's signed certificate"
	openssl x509 -in certs/server-cert.pem -noout -text

	# 4. Generate client's private key and certificate signing request (CSR)
	openssl req -newkey rsa:4096 -nodes -keyout certs/client-key.pem -out certs/client-req.pem -subj "/C=UK/ST=UK/L=UK/O=M1L0 Builder/CN=localhost/emailAddress=example@example.com"

	# 5. Use CA's private key to sign client's CSR and get back the signed certificate
	openssl x509 -req -in certs/client-req.pem -days 60 -CA certs/ca-cert.pem -CAkey certs/ca-key.pem -CAcreateserial -out certs/client-cert.pem -extfile certs/client-ext.cnf

	echo "Client's signed certificate"
	openssl x509 -in certs/client-cert.pem -noout -text