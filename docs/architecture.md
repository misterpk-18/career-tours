# Architecture

How Career Tours is deployed and how a request travels through it. This is the
source of truth for the runtime shape and for the build, deploy and publish
procedures. The API contract those procedures serve is in
[api-contract.md](api-contract.md).

Verified against the live AWS account on **2026-08-17**.

---

## Target architecture

```text
                    Users
                      │
                      ▼
        React (Vercel / S3 + CloudFront)
                      │
                 HTTPS Requests
                      │
                      ▼
              API Gateway (HTTP API)
                      │
                      ▼
                 AWS Lambda
                      │
      Flask + Mangum + SQLAlchemy
                      │
      ┌───────────────┴────────────────┐
      ▼                                ▼
   Neon PostgreSQL                  Amazon S3
      │                                │
      └───────────────┬────────────────┘
                      ▼
                  OpenAI API
```

This is now what is deployed. API Gateway became viable only once the long endpoints were
converted to background jobs — see [The 30-second wall](#the-30-second-wall).

The Lambda **Function URL** still exists and still works. It is kept deliberately as a
fallback while the CloudFront path beds in; retiring it means setting its `AuthType` to
`AWS_IAM` or deleting it, and that should wait until real traffic has proven the new route.

---

## What is actually deployed

AWS account **307857432997**, region **ap-south-1** (Mumbai).

| Component | Value |
|---|---|
| Lambda function | `career-tours-api` |
| Package type | **Image** (not zip) — ECR `307857432997.dkr.ecr.ap-south-1.amazonaws.com/career-tours-api:latest`, ~237 MB compressed / 1.07 GB on disk |
| Architecture | **arm64** — builds must target it explicitly (`docker buildx --platform linux/arm64`) |
| Memory / timeout | 1024 MB / **300 s** |
| Execution role | `career-tours-lambda-role-kpgs1hwq` |
| Log group | **`/aws/lambda/career-tours-lambda`** — overridden, so the default `/aws/lambda/career-tours-api` group is empty |
| Public entry point | **`https://nipunacareers.com`** (and `www.`) → CloudFront `E1TW6HR68G4A7T` |
| Origin URL | `d2g1lg63sloe7m.cloudfront.net` — still serves, unaliased |
| DNS | Route53 zone `Z0520838K2KUFGOJETR5`, A + AAAA alias records on apex and `www` |
| TLS | ACM `190bc4f6-c33a-4885-a3d5-5d025297da21` in **us-east-1** — CloudFront accepts certificates from that region only, regardless of where the distribution serves. `sni-only`, TLSv1.2_2021 |
| API Gateway | HTTP API `722dql67f0`, `$default` route + `$default` stage, payload format 2.0, 30s integration timeout |
| Frontend | S3 `career-tours-web`, private, readable only by that distribution via OAC `E2L96DF7Q3K1VQ` |
| Fallback entry point | Lambda Function URL, `AuthType: NONE` — still live, kept until CloudFront is proven |
| Database | Neon Postgres, `ep-restless-math-aznw9s4g.c-3.ap-southeast-1.aws.neon.tech`, database `neondb` |
| Object storage | S3 bucket `career-tours-bkt` (resume files) |
| Ephemeral disk | 512 MB at `/tmp` — the only writable path |

The Function URL is
`https://m2542kqtvzbylgowv66f72grwe0gxifg.lambda-url.ap-south-1.on.aws`.
`GET /` returns `{"status": "ok"}` and `GET /db-test` returns `{"database": "neondb"}`.

### Two facts about the database worth knowing before you debug anything

1. **The Neon endpoint is unpooled.** The host has no `-pooler` suffix, so every
   connection is a direct one. Moving to the pooler endpoint is an env-var-only change
   and is safe for this codebase — every repository is plain `text()` SQL followed by
   `commit()`, with no `LISTEN`, no advisory locks and no server-side cursors.
2. **It is cross-region.** Neon is in `ap-southeast-1` (Singapore) while the Lambda is in
   `ap-south-1` (Mumbai) — roughly 60–75 ms round trip per query. This is not academic:
   `services/matching/ranking.py` issues one `get_skills()` query *per occupation* in a
   Python loop, so that N+1 costs N × ~65 ms of pure network before any LLM call runs.

---

## The request path

1. The browser calls a **relative** `/api/...` URL. `frontend/src/services/api.js` sets
   `API_BASE_URL = '/api'` and there are **no `import.meta.env` variables anywhere in the
   frontend** — there is deliberately no per-environment build.
2. Whatever fronts the static bundle must therefore route `/api` to the Lambda on the
   **same origin** (a Vercel rewrite, or a CloudFront `/api/*` behaviour). This is what
   keeps CORS out of the picture entirely; `flask-cors` is not a dependency and the Flask
   app sets no CORS headers of its own. The Function URL's wildcard CORS config is the
   only thing answering preflight today.
3. Lambda invokes `app.handler`. `backend/app.py` builds `Mangum(WsgiToAsgi(app))` —
   Mangum speaks ASGI, Flask is WSGI, and `asgiref` bridges them. The same `app` object
   and the same blueprints serve every runtime.
4. Blueprints already carry the `/api` prefix (`/api/auth`, `/api/students`, `/api/resumes`,
   `/api/recommendations`, `/api/projects`), so Mangum's `api_gateway_base_path` is left at
   its default `"/"` and no path stripping happens. When API Gateway lands it must use the
   **`$default` stage**, which serves paths with no stage prefix, so this stays true.
5. The handler reads and writes Neon over TLS, puts resume files in S3, and calls the
   OpenAI and Hugging Face APIs over the internet. The function is **not in a VPC**, which
   is what makes those outbound calls work without a NAT gateway.

### File uploads

`/tmp` is the only writable filesystem. `backend/api/resumes/routes.py` sets
`UPLOAD_DIR = Path("/tmp/uploads/resumes")` and creates it **at import time** — a relative
path would resolve under the read-only `/var/task` and take down the whole app before a
single request was served. Files are parsed, pushed to S3, and deleted on every code path.

Two size limits apply, and the smaller one is not the one in the code:

- `MAX_FILE_SIZE_MB = 10` is the application check.
- A **synchronous Lambda invocation payload caps at 6 MB**, and both Function URLs and
  API Gateway base64-encode binary bodies (~1.33× expansion). The real ceiling is ≈4.4 MB,
  and a file over it fails at the platform edge with an opaque error before Flask sees it.

---

## The 30-second wall

**API Gateway HTTP API caps its integration timeout at 30 seconds, and that limit cannot be
raised.** Two endpoints exceed it, and **both are now async jobs** — which is what made the
API Gateway front door viable at all:

| Endpoint | Duration | Why | Async |
|---|---|---|---|
| `POST /api/recommendations/projects/<id>/generate` | **~73-110 s** | HF embeddings + a fan-out of `gpt-5` summary calls | `?async=1` |
| `POST /api/resumes/<id>/extract-skills` | **~25-41 s** | one `gpt-5` `responses.parse` call | `?async=1`, except the cached branch |

Synchronously, the first would 504 and the second would fail *intermittently* — harder to
diagnose than failing every time, because it straddles the limit rather than clearing it.

The fix is not a bigger timeout — it is **submit-then-poll async jobs**: the request path
writes a job row and returns `202` with a `job_id` in well under a second (measured: 0.72s
and 0.99s), the Lambda invokes *itself* with `InvocationType='Event'` to do the work out of
band, and the frontend polls `GET /api/jobs/<job_id>` until a terminal status arrives.

Both routes keep their synchronous behaviour when `?async=1` is absent, for Postman and ops.
`extract-skills` additionally stays synchronous **even with `?async=1`** when the project's
skills are already stored: that branch is one SELECT and answers in well under a second, so
routing it through a job would be slower for nothing. The route therefore returns either a
finished result or a 202, and clients branch on the presence of `job_id`.

Job submission — create the row, treat the partial unique index's `IntegrityError` as a
double submit and return the in-flight job, delete the row if the enqueue fails — lives once
in `backend/api/job_submission.py`.

One Lambda-specific trap that rules out the obvious shortcut: **a background thread does not
work here.** Lambda freezes the execution environment the moment the handler returns — CPU
drops to approximately zero, and the sandbox is only thawed by a later invocation that may
not even be the same sandbox. A 73-second thread would make partial, unpredictable progress
and hold a Neon connection open while frozen.

---

## Configuration

Everything is supplied as Lambda environment variables. There is no `.env` file in the image,
so a missing variable is a runtime failure, not a fallback.

| Variable | Notes |
|---|---|
| `DB_USER`, `DB_PASSWORD` | default to `""` |
| `DB_HOST`, `DB_PORT`, `DB_NAME` | **no defaults** — a missing one yields the literal string `None` inside the URL |
| `DB_SSLMODE` | defaults to `require`; Neon rejects plaintext |
| `SECRET_KEY` | JWT signing; defaults to `dev-secret-change-me` |
| `JWT_EXPIRY_HOURS` | defaults to `24` |
| `OPENAI_API_KEY` | models are hardcoded: `gpt-5` for extraction, `gpt-5-mini` for summaries |
| `HF_TOKEN` | Hugging Face Inference API, `sentence-transformers/all-MiniLM-L6-v2` |
| `AWS_BUCKET_NAME` | **no default** — `S3Service` raises rather than guess a bucket |
| `AWS_ACCESS_KEY`, `AWS_SECRET_KEY` | note the **non-standard names**; the reserved `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` cannot be set as Lambda env vars |
| `AWS_REGION` | defaults to `ap-south-1` |
| `LANGSMITH_*` | read by the `langsmith` SDK itself, not by any code in this repo |

`S3Service` passes its keys to `boto3.client` explicitly. If both are `None`, boto3 falls
through to its default credential chain and picks up the **execution role** — so dropping the
static keys later is an env-var change with no code change, once the role has
`s3:PutObject`/`s3:GetObject` on `arn:aws:s3:::career-tours-bkt/*`.

### Known risk: secrets are plaintext

Every secret above — including `OPENAI_API_KEY`, `HF_TOKEN`, `LANGSMITH_API_KEY`,
`DB_PASSWORD` and `SECRET_KEY` — is stored in plaintext in the Lambda's environment
configuration, readable by anyone holding `lambda:GetFunctionConfiguration`. The Function URL
in front of it is entirely unauthenticated (`AuthType: NONE`). Moving these to Secrets Manager
or SSM Parameter Store requires an execution-role policy change.

---

## IAM: what the deploy user can do

Deploys run as `arn:aws:iam::307857432997:user/career-tours-deployer`.

An earlier revision of this document listed `apigateway:GET`, `iam:*`, `s3:ListAllMyBuckets`,
`s3:ListBucket`, `s3:GetBucketLocation` and `cloudfront:ListDistributions` as **denied** to this
user, and drew conclusions from that — that it could not read an API Gateway, attach execution-role
policies, or inspect CloudFront and the bucket. **That list is wrong.** Every one of those actions
simulates as `allowed`, along with `ecr:PutImage`, `lambda:UpdateFunctionCode`,
`route53:ChangeResourceRecordSets` and `ses:SendEmail`. The permissions were presumably widened
after the note was written and it was never revisited.

Check the real answer rather than trusting a list here, which will drift again:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::307857432997:user/career-tours-deployer \
  --action-names iam:PutRolePolicy cloudfront:ListDistributions apigateway:GET \
  --query 'EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}' --output table
```

Note that `simulate-principal-policy` evaluates policy, not the API call: an action can simulate
as `allowed` and still fail on a resource-level condition or an SCP.

---

## Deploying

```bash
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS --password-stdin 307857432997.dkr.ecr.ap-south-1.amazonaws.com

docker buildx build --platform linux/arm64 \
  --provenance=false --sbom=false \
  --output type=image,oci-mediatypes=false,push=true \
  -t 307857432997.dkr.ecr.ap-south-1.amazonaws.com/career-tours-api:latest .

aws lambda update-function-code --function-name career-tours-api --region ap-south-1 \
  --image-uri 307857432997.dkr.ecr.ap-south-1.amazonaws.com/career-tours-api:latest
aws lambda wait function-updated --function-name career-tours-api --region ap-south-1
```

> The image URI is written out in full rather than held in a variable on purpose.
> In zsh, `$ECR:latest` applies `:l` as a parameter modifier — it lowercases the
> value and leaves `atest` behind, so the push goes to a repository named
> `career-tours-apiatest` and fails with "repository does not exist". Braces
> (`${ECR}:latest`) also work; the literal cannot be got wrong.

> **The three build flags are not optional.** Since Buildx 0.10 the default is to
> attach provenance and SBOM attestations, which wraps the image in an
> `application/vnd.oci.image.index.v1+json` manifest. Lambda accepts only
> `application/vnd.docker.distribution.manifest.v2+json` and rejects the update with:
>
> ```
> InvalidParameterValueException: The image manifest, config or layer media type
> for the source image ... is not supported.
> ```
>
> The image pushes to ECR perfectly happily first, so the failure surfaces one step
> later than its cause. Check what actually landed with:
>
> ```bash
> aws ecr describe-images --repository-name career-tours-api --region ap-south-1 \
>   --query 'sort_by(imageDetails,&imagePushedAt)[-1].imageManifestMediaType'
> ```

The `Dockerfile` copies `backend/` **into** `${LAMBDA_TASK_ROOT}` rather than alongside it,
because the Python packages use bare imports (`from api.auth.routes import auth_bp`) and so
`backend/` must be the package root. `CMD ["app.handler"]` is a handler string, not a shell
command.

Logs — remember the group override:

```bash
aws logs tail /aws/lambda/career-tours-lambda --region ap-south-1 --since 15m --follow
```

### Testing the image locally

The AWS base image ships the runtime interface emulator, so the exact event shape API Gateway
will send can be replayed before deploying:

```bash
docker run --rm -p 9000:8080 --env-file .env career-tours-api:local

curl -s localhost:9000/2015-03-31/functions/function/invocations -d '{
  "version":"2.0","routeKey":"$default","rawPath":"/db-test","headers":{},
  "requestContext":{"http":{"method":"GET","path":"/db-test","sourceIp":"1.2.3.4"}},
  "isBase64Encoded":false }'
```

If you ever see `"The adapter was unable to infer a handler to use for the event"`, the event
you sent matched none of Mangum's four recognised shapes (ALB, API Gateway v1/v2, Lambda@Edge).
That is a malformed test payload, not a broken function.

---

## Publishing the frontend

CloudFront serves the SPA from S3 and routes `/api/*` to the HTTP API, so `/api` stays
same-origin and `frontend/src/services/api.js` needs no base URL and no CORS.

```bash
cd frontend && npm run build && cd ..

# hashed filenames make immutable caching safe
aws s3 sync frontend/dist/ s3://career-tours-web/ --delete --exclude index.html \
  --cache-control "public,max-age=31536000,immutable"

# index.html must never be cached, or users keep booting the previous build
aws s3 cp frontend/dist/index.html s3://career-tours-web/index.html \
  --cache-control "no-store" --content-type "text/html"

aws cloudfront create-invalidation --distribution-id E1TW6HR68G4A7T --paths "/index.html"
```

Only `/index.html` needs invalidating: every other asset carries a content hash in its
filename, so a new build writes new objects rather than replacing cached ones.

### How a deep link finds the SPA

A path like `/projects/<id>` is React Router's, not S3's, so the bucket has no such object. The
CloudFront function **`career-tours-spa-fallback`** rewrites any URI whose last segment has no
file extension to `/index.html`. It is attached as **viewer-request on the default behaviour
only**, so `/api/*` — a separate behaviour — never sees it, and `/assets/index-<hash>.js` is
served as itself.

This deliberately replaced two distribution-wide `CustomErrorResponses` mapping `403`/`404` to
`/index.html` with a `200`. Custom error responses cannot be scoped to one behaviour, so they
also rewrote genuine API errors: `GET /api/nope` returned `200 text/html`, and an unknown id
returned the SPA shell instead of `404 {"error": "…"}` — which made `useJob` poll forever on an
undefined status, and would have made the course page report the wrong failure.

**Both halves are required.** The function existed and was published LIVE for a while with
nothing attached, while the error responses stayed in place — so the bug was live even though
everything looked configured. Check `DefaultCacheBehavior.FunctionAssociations`, not just
`list-functions`:

```bash
aws cloudfront get-distribution-config --id E1TW6HR68G4A7T \
  --query 'DistributionConfig.{Fn:DefaultCacheBehavior.FunctionAssociations,Errors:CustomErrorResponses.Quantity}'
# want: Fn.Quantity == 1, Errors == 0
```
