.PHONY: start
start:
	uvicorn main:app --reload --port 9000

.PHONY: format
format:
	black .
	isort .

build-dir:
	mkdir -p .build

build: build-dir
	CGO_ENABLED=0 go build -o .build/gateway github.com/jlewi/roboweb/gateway/cmd


build-image-submit:
	COMMIT=$$(git rev-parse HEAD) && \
					gcloud builds submit --project=$(PROJECT) --async --config=cloudbuild.yaml \
					--substitutions=COMMIT_SHA=local-$${COMMIT} \
					--format=yaml > .build/gcbjob.yaml

build-image-logs:
	JOBID=$$(yq e ".id" .build/gcbjob.yaml) && \
					gcloud --project=$(PROJECT) builds log --stream $${JOBID}

build-image: build-dir build-image-submit build-image-logs	