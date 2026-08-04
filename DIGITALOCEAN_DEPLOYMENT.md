# DigitalOcean App Platform migration

This repository can deploy the public API and the research worker from the same
Dockerfile. The services share durable state through DigitalOcean Spaces, not
through their temporary container filesystems.

## 1. Create Spaces

1. Create a private Space in the same DigitalOcean region as the app. For the
   provided app specification, use Singapore (`sgp1`).
2. Create a dedicated Spaces access key with read/write access to only this
   Space.
3. Keep the Space private. Application assets and job data remain under the
   `architect/` prefix.

## 2. Migrate existing data

Before switching DNS, copy the current COS prefix to the Space with an
S3-compatible migration tool such as rclone. Preserve object names exactly:

```text
architect/jobs/...
architect/cases/...
```

Verify the object count and a sample of case packages before cutover. Do not
delete COS until the DigitalOcean deployment has processed a real research job.

## 3. Create the App Platform app

1. In App Platform, create an app from the GitHub repository.
2. Select the branch in `.do/app.yaml`, or change that branch to your release
   branch before deployment.
3. Upload or paste `.do/app.yaml` in the App Spec editor.
4. Add the variables listed at the bottom of that file as **encrypted,
   app-level, runtime** variables. Never store credentials in this repository.
5. Deploy both components. `architect-api` is public on port `8080`; the worker
   has no public endpoint.

## 4. Verify before DNS cutover

1. `GET /healthz` returns HTTP 200.
2. `GET /readyz` returns `{ "status": "ready", "storage": "ready" }`.
3. Submit a test research job from the site.
4. Verify that the worker completes it and that its task and result objects
   appear in Spaces.
5. Point the custom domain to App Platform only after the checks pass.

## Storage configuration

Set `ARCHITECT_STORAGE_BACKEND=s3` to enable the S3-compatible backend. The
legacy `cos` backend remains available for rollback during migration.
