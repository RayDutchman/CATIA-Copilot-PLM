# docdoku-plm-conversion-service

DocDokuPLM microservice that performs file format conversions

Run dev server

```
cd conversion-service
./mvnw compile quarkus:dev
```

Package and build image

./build.sh

Notes

- The Docker image now installs Python dependencies at build time from
	`requirements-converter.txt`.
- Large wheel binaries under `wheels/` are not required in Git anymore and are
	intentionally excluded from version control.
