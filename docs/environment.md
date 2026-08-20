# Environment and credentials

One place for every environment variable the system reads, what consumes it, where
its value is stored, and **what permission the credential behind it actually carries**.
Written for the two migrations on the horizon — a new AWS account and a new database —
so each entry says what a replacement has to be able to do, not just what it is called.

Verified against the live AWS account and the deployed Lambda on **2026-08-20**.
Runtime shape, request path and deploy commands stay in [architecture.md](architecture.md);
this document is only configuration and identity.

No secret values are recorded here. The values live in exactly two places, listed under
[Where the values live](#where-the-values-live).

---

## Every variable

`(default)` means the code supplies one, so a missing variable is silent rather than loud.
Secrets are marked **S**.

| Variable | S | Read by | Set locally | Set on Lambda | Default | Notes |
|---|---|---|---|---|---|---|
| `DB_HOST` | | [config/database.py:16](../backend/config/database.py#L16) | yes | yes | none | Missing yields the literal string `None` in the URL |
| `DB_PORT` | | [config/database.py:17](../backend/config/database.py#L17) | yes | yes | none | `5432` |
| `DB_NAME` | | [config/database.py:18](../backend/config/database.py#L18) | yes | yes | none | `neondb` |
| `DB_USER` | | [config/database.py:14](../backend/config/database.py#L14) | yes | yes | `""` | Empty string produces a URL with no user, which fails obscurely |
| `DB_PASSWORD` | **S** | [config/database.py:15](../backend/config/database.py#L15) | yes | yes | `""` | URL-quoted by `quote_plus`, so specials are safe |
| `DB_SSLMODE` | | [config/database.py:11](../backend/config/database.py#L11) | yes | yes | `require` | Neon rejects plaintext; never lower this |
| `SECRET_KEY` | **S** | [config/database.py:23](../backend/config/database.py#L23) | yes | yes | `dev-secret-change-me` | JWT signing. The default is a working key — a wiped env map signs tokens with a public string |
| `JWT_EXPIRY_HOURS` | | [config/database.py:24](../backend/config/database.py#L24) | yes | yes | `24` | `int()` — a non-numeric value crashes at import |
| `OPENAI_API_KEY` | **S** | [services/llm/openai_service.py:150](../backend/services/llm/openai_service.py#L150) | yes | yes | none | Model names are hardcoded, not configurable |
| `HF_TOKEN` | **S** | [services/matching/skill_matcher.py:56](../backend/services/matching/skill_matcher.py#L56), [services/llm/gemma_service.py:160](../backend/services/llm/gemma_service.py#L160) | yes | yes | none | Two different HF products behind one token — see below |
| `AWS_BUCKET_NAME` | | [services/storage/s3_service.py:22](../backend/services/storage/s3_service.py#L22) | yes | yes | none, **raises** | `career-tours-bkt`. The only var whose absence is a clean error |
| `AWS_ACCESS_KEY` | **S** | [services/storage/s3_service.py:13](../backend/services/storage/s3_service.py#L13) | yes | **no** | `None` | Non-standard name on purpose; see [reserved names](#reserved-and-platform-supplied-names) |
| `AWS_SECRET_KEY` | **S** | [services/storage/s3_service.py:14](../backend/services/storage/s3_service.py#L14) | yes | **no** | `None` | Absent on Lambda so boto3 falls through to the execution role |
| `AWS_REGION` | | [services/storage/s3_service.py:15](../backend/services/storage/s3_service.py#L15) | yes | **cannot be** | `ap-south-1` | Reserved by Lambda, which supplies it |
| `LANGSMITH_TRACING` | | `langsmith` SDK | yes | yes | off | `true`/`false`; no repo code reads it |
| `LANGSMITH_ENDPOINT` | | `langsmith` SDK | yes | yes | SDK default | `https://api.smith.langchain.com` |
| `LANGSMITH_API_KEY` | **S** | `langsmith` SDK | yes | yes | none | Tracing only; nothing functional depends on it |
| `LANGSMITH_PROJECT` | | `langsmith` SDK | yes | yes | `default` | Current value **contains a space** — see the quoting trap below |
| `CT_TRACE_INIT` | | [app.py:12](../backend/app.py#L12) | no | no | `1` (on) | Set `0` to silence import-timing lines |
| `APP_BASE_URL` | | [services/email/mailer.py](../backend/services/email/mailer.py) | optional | optional | `https://nipunacareers.com` | Base for the verify/reset links in emails. Set only if the public URL changes |
| `MAIL_SENDER` | | [services/email/mailer.py](../backend/services/email/mailer.py) | optional | optional | `Nipuna Careers <no-reply@nipunacareers.com>` | From header for all SES email; the address must be under a verified SES identity |
| `DEEPINFRA_API_KEY` | **S** | **nothing** | yes | no | — | Dead. No reference anywhere in the repo; delete it rather than carry it forward |

**The frontend has no environment variables at all.** `frontend/src/services/api.js` hardcodes
a relative `API_BASE_URL = '/api'` and there is no `import.meta.env` anywhere in `frontend/src`.
The bundle is therefore environment-independent: one build works behind any front door that
routes `/api` to the backend on the same origin. Nothing in a migration needs a frontend rebuild
for configuration reasons.

### Reserved and platform-supplied names

| Name | Why it matters |
|---|---|
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Reserved by Lambda. Including any of them in `update-function-configuration` fails with `InvalidParameterValueException`. This is the entire reason the code reads the non-standard `AWS_ACCESS_KEY`/`AWS_SECRET_KEY` |
| `AWS_LAMBDA_FUNCTION_NAME` | Supplied by the platform, read at [services/jobs/dispatch.py:39](../backend/services/jobs/dispatch.py#L39). It is the **switch between the two async-job mechanisms**: present → the function invokes itself with `InvocationType='Event'`; absent → a local background thread. Never set it by hand off Lambda, or dispatch will try to invoke a function that isn't there |

### Two traps in the current values

1. **`LANGSMITH_PROJECT` is `my first one`.** The space means `source .env` in bash fails with
   `line 9: first: command not found` unless the value is quoted. Lambda's env map and
   `--env-file` tolerate it. Quote it, or rename the LangSmith project.
2. **`SECRET_KEY` has a working default.** Every other secret fails loudly when missing;
   this one silently signs JWTs with `dev-secret-change-me`. After any env-map replacement,
   confirm it is present before trusting a login.

---

## What each credential is allowed to do

The point of this section: **every AWS credential in play today is over-privileged**, and a
migration is the natural moment to fix that. Each entry gives what it holds now and the
minimum a replacement needs.

### `AWS_ACCESS_KEY` / `AWS_SECRET_KEY` — IAM user `career_tours_s3_user`

Account `307857432997`. Access key `AKIAUPLN3UGSVZX7G25D`, active since 2026-08-03. No groups,
no inline policies, six attached managed policies:

`AdministratorAccess`, `AmazonS3FullAccess`, `AmazonElasticContainerRegistryPublicFullAccess`,
`AWSLambda_FullAccess`, `AmazonS3ObjectLambdaExecutionRolePolicy`, `AmazonS3FilesReadOnlyAccess`

**This is an account-admin key sitting in a `.env` file**, and the five policies after the first
are noise — `AdministratorAccess` already implies all of them. What the code does with it is two
S3 calls: `upload_file` and `generate_presigned_url`
([s3_service.py](../backend/services/storage/s3_service.py)).

Minimum for a replacement:

```json
{ "Effect": "Allow",
  "Action": ["s3:PutObject", "s3:GetObject"],
  "Resource": "arn:aws:s3:::<bucket>/*" }
```

Presigned GET URLs are signed locally from these same credentials, so no extra action is needed
for previews. Note this key is **only used off-Lambda** (local dev and any script that uploads);
in production S3 goes through the execution role.

### The Lambda execution role — `career-tours-lambda-role-kpgs1hwq`

What the deployed backend can actually reach. Four policies:

| Policy | Kind | Grants | Used by |
|---|---|---|---|
| `AWSLambdaBasicExecutionRole-2e51095d-…` | managed (customer) | `logs:CreateLogGroup` account-wide; `logs:CreateLogStream`/`PutLogEvents` **only on `/aws/lambda/career-tours-lambda`** | All logging |
| `AmazonS3FullAccess` | AWS managed | S3 on everything | Resume upload/preview — needs only `s3:PutObject`/`s3:GetObject` on `arn:aws:s3:::career-tours-bkt/*` |
| `career-tours-self-invoke` | inline | `lambda:InvokeFunction` on `arn:aws:lambda:ap-south-1:307857432997:function:career-tours-api` | The async-job dispatcher. Correctly scoped to its own ARN |
| `career-tours-ses-send` | inline | `ses:SendEmail` + `ses:SendRawEmail` on `Resource: "*"` | The auth email flow ([services/email/mailer.py](../backend/services/email/mailer.py)): verification, OTP, and reset mail. **Was** scoped to `identity/nipunacareers.com`, which failed with `AccessDenied` naming the *recipient* identity — SES evaluates the action against recipients too, so the resource was widened to `*` (SES still enforces that the From must be a verified identity, so this is the standard, safe send policy). See [architecture.md](architecture.md#email-ses) for the sandbox caveat |

Two things this pins down:

- **The log-group grant is name-specific.** The function is `career-tours-api` but its
  `LoggingConfig.LogGroup` points at `/aws/lambda/career-tours-lambda`, which is what this policy
  allows. Renaming either the function or the group without editing this policy makes the Lambda
  stop logging — and a Lambda that cannot log fails invisibly.
- **S3 works on Lambda without any key** precisely because `AWS_ACCESS_KEY`/`AWS_SECRET_KEY` are
  absent from the env map: `boto3.client(..., aws_access_key_id=None)` falls through to the
  default credential chain and picks up this role. Adding those variables to Lambda would
  silently switch production S3 back onto the static key.

SES is now used by the auth email flow (verification, OTP, reset). The account is **still in
the SES sandbox** (`ProductionAccessEnabled: false`, 200 messages/day, 1/sec), so it can only
deliver to **verified recipient identities** — an unverified recipient is rejected at send with
`MessageRejected: Email address is not verified`. Verify a single test inbox with
`aws sesv2 create-email-identity --email-identity <addr>` (AWS mails it a confirm link); the real
fix is **production access** (SES console → Account dashboard → Request production access), after
which any recipient works with no code change.

### The deploy credential — IAM user `career-tours-deployer`

Access key `AKIAUPLN3UGSRMY4B7YW`, active since 2026-08-05. Attached: `AdministratorAccess`,
`AmazonEC2ContainerRegistryFullAccess`, `AWSLambda_FullAccess`. Again admin, with two redundant
policies alongside.

Older notes in this repo and in project memory described this user as scoped down — denied
`apigateway:GET`, `iam:*`, `cloudfront:*`, `s3:ListBucket`. **That is obsolete and was already
wrong by 2026-08-15.** It holds `AdministratorAccess`; IAM reads and writes work, which is how
this document was assembled. Do not plan around the old denial list.

What the documented deploy and publish procedures actually exercise:

| Step | Actions |
|---|---|
| Push the image | `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage`, `ecr:DescribeImages` |
| Update the function | `lambda:UpdateFunctionCode`, `lambda:GetFunction`, `lambda:GetFunctionConfiguration`, `lambda:UpdateFunctionConfiguration` (env-map changes) |
| Publish the frontend | `s3:ListBucket` + `s3:PutObject`/`DeleteObject` on `career-tours-web/*`, `cloudfront:CreateInvalidation`, `cloudfront:GetDistributionConfig` |
| Read logs | `logs:FilterLogEvents`, `logs:DescribeLogGroups` on `/aws/lambda/career-tours-lambda` |

Anything beyond that list — creating the distribution, editing Route53, attaching role policies,
requesting the ACM certificate — is one-time setup work, not deploy work. Give a replacement
deployer the table above and keep the setup work behind a separate admin identity.

### `DB_*` — the Neon Postgres role

`neondb_owner` on database `neondb`, endpoint
`ep-restless-math-aznw9s4g.c-3.ap-southeast-1.aws.neon.tech`. It is Neon's project owner role:
full DDL and DML on `public`, which is what the migrations in `backend/migrations/` and the
loaders in `backend/scripts/` assume. The app itself only ever needs DML plus `SELECT`.

Four properties of this endpoint that a migration should decide about deliberately:

1. **It is cross-region** — Singapore (`ap-southeast-1`) while the Lambda is in Mumbai
   (`ap-south-1`), ~74 ms per round trip. Co-locating the replacement is the single largest
   latency win available.
2. **It is unpooled** — no `-pooler` in the host. Switching is env-var-only and safe for this
   codebase (raw `text()` SQL and `commit()`; no `LISTEN`, advisory locks or server-side cursors).
3. **It autosuspends** — the first query after idle can time out outright. `pool_pre_ping` in
   `app.py` exists for this; retry once before believing a connection failure.
4. **There is one database for all environments.** `.env` locally points at the same endpoint the
   Lambda uses, so local runs write to production. The migration is the opportunity to split
   local from production; until then see the warning in
   [Where the values live](#where-the-values-live).

Ceiling to size before a cohort sits assessments at once: each Lambda sandbox holds one
connection (`pool_size: 1`), so concurrent invocations map roughly 1:1 onto Neon connections.

### `OPENAI_API_KEY`

Needs: chat/responses access to **`gpt-5`** (resume skill extraction, `responses.parse`) and
**`gpt-5-mini`** (career and course summaries). Both model names are hardcoded in
[services/llm/openai_service.py](../backend/services/llm/openai_service.py) — a replacement key
on a project without access to those exact models fails at call time, not at boot.

Failure mode worth recognising: a quota-exhausted key returns `429 insufficient_quota`, which
aborts the whole recommendation generation even though the non-LLM career ranking succeeded.
That reads like a code bug and is a billing problem.

Also consumed by three offline scripts — `extract_course_profiles.py`,
`author_career_skills.py`, `generate_section_questions.py` — so whoever re-runs a data pipeline
needs a key too, not just the deployment.

### `HF_TOKEN`

One token, two different Hugging Face products, and a replacement must cover both:

| Consumer | Product | Needs |
|---|---|---|
| [skill_matcher.py:56](../backend/services/matching/skill_matcher.py#L56) | Inference API, `sentence-transformers/all-MiniLM-L6-v2` feature extraction | Inference permission. **On the request path** — without it, recommendation generation fails outright |
| [gemma_service.py:160](../backend/services/llm/gemma_service.py#L160) | Inference **Router** (`chat.completions` through an OpenAI-compatible base URL, optionally pinned to a provider like `together`/`novita`/`cerebras`) | Router access and **inference-provider credits** — this one bills |

The router path is offline only (`generate_section_questions.py` builds the question corpus), so a
token that can do inference but not routing breaks corpus generation while leaving the live app fine.
Nothing runs a model in-process; there is no `torch` dependency.

### `LANGSMITH_*`

Observability only. No repo code reads these — the `langsmith` SDK picks them up itself, and
`wrap_openai` in `openai_service.py` is what emits traces. Setting `LANGSMITH_TRACING=false` or
dropping the key entirely costs traces and nothing else. Lowest-stakes group here; migrate it last.

### `SECRET_KEY`

Signs and verifies every JWT. Rotating it invalidates all outstanding sessions — a forced logout
for every user, which is fine as long as it is expected. It must be **identical** anywhere the API
runs, or tokens minted by one runtime are rejected by another.

---

## Where the values live

Two copies, no more:

| Copy | What | How to change |
|---|---|---|
| Repo-root `.env` | 20 keys, git-ignored. Feeds local dev (`load_dotenv()`), every `backend/scripts/` run, and `docker run --env-file .env` | Edit the file |
| Lambda env map on `career-tours-api` | 15 keys | `aws lambda update-function-configuration` |

There is **no `.env` inside the container image** — the `Dockerfile` copies only `requirements.txt`
and `backend/`, and `.env` is in `.dockerignore`. A missing variable in production is a runtime
failure with no fallback.

> **Env updates replace the whole map.** `update-function-configuration --environment` is not a
> merge. Read the current map, merge locally, write it back — this has already cost one incident
> where `DB_USER` vanished and Postgres got a URL with an empty user.

> **The repo `.env` points at production.** `DB_HOST` there is the same Neon endpoint the Lambda
> uses. Running the app locally, opening a Flask shell or running a smoke test writes to the live
> database. Before any write-path test, check that `DATABASE_URL.split('@')[1]` is what you think
> it is. Reading is safe and is the fastest way to check real schema state.

### Current drift between the two

| Variable | Local `.env` | Lambda | Why |
|---|---|---|---|
| `AWS_ACCESS_KEY`, `AWS_SECRET_KEY` | set | absent | **Deliberate.** Absence is what makes production S3 use the execution role |
| `AWS_REGION` | set | absent | Reserved on Lambda; the platform supplies it |
| `DEEPINFRA_API_KEY` | set | absent | Dead key, no consumer. Drop it from `.env` |

The other 15 are present in both and should stay in sync. Nothing else differs — no variable is
set on Lambda but missing locally.

An EC2 deployment (`3.110.122.199`) held a third copy at `/home/ec2-user/career-tours/.env`
against a *local* Postgres named `career_tours`. That runtime is retired; only mentioned so an old
`.env` found on that box is recognised as stale and not restored.

---

## Not environment variables, but account-bound

These are hardcoded in docs, commands and AWS resources rather than configuration, and every one
of them changes when the account does. Listed so the migration inventory is complete.

| Thing | Current value |
|---|---|
| AWS account | `307857432997`, region `ap-south-1` |
| Lambda | `career-tours-api` — image, arm64, 1024 MB, 300 s |
| ECR image | `307857432997.dkr.ecr.ap-south-1.amazonaws.com/career-tours-api:latest` |
| Log group | `/aws/lambda/career-tours-lambda` (overridden; matches the role policy, not the function name) |
| HTTP API | `722dql67f0`, `$default` route and stage, 30 s integration timeout |
| CloudFront | `E1TW6HR68G4A7T`, origin `d2g1lg63sloe7m.cloudfront.net` |
| CloudFront function | `career-tours-spa-fallback`, viewer-request on the **default behaviour only** |
| Web bucket | `career-tours-web` — private; bucket policy allows `s3:GetObject` to `cloudfront.amazonaws.com` only, conditioned on `AWS:SourceArn` = distribution `E1TW6HR68G4A7T` (OAC `E2L96DF7Q3K1VQ`) |
| Resume bucket | `career-tours-bkt` — `ap-south-1`, **no bucket policy**, and public access block is **fully off** (all four flags `false`). Access is by IAM only today; the guard rail against an accidental public policy is not in place. Turn all four on in the new account |
| Function URL | `https://m2542kqtvzbylgowv66f72grwe0gxifg.lambda-url.ap-south-1.on.aws`, `AuthType: NONE` — unauthenticated fallback, still live |
| DNS / TLS | Route53 `Z0520838K2KUFGOJETR5`; ACM `190bc4f6-c33a-4885-a3d5-5d025297da21` in **us-east-1** (CloudFront takes certs from there only) |
| SES | Identities `nipunacareers.com`, `manojtungala2601@gmail.com`; **sandbox**, 200/day, 1/sec |

### Known accepted risk

Every secret above is stored **plaintext** in the Lambda environment configuration, readable by
anyone holding `lambda:GetFunctionConfiguration` — and two identities in this account hold
`AdministratorAccess`, one of whose keys sits in a `.env` on a laptop. In front of it, the
Function URL is unauthenticated. Moving to Secrets Manager or SSM Parameter Store needs an
execution-role policy change and a small change at the read sites; the account migration is the
cheapest moment to do it, because the secrets have to be re-entered anyway.

---

## Migration checklists

### Moving to a new AWS account

1. **Create three identities, not two admins.** A deploy user with the ECR/Lambda/S3/CloudFront
   actions in the [deployer table](#the-deploy-credential--iam-user-career-tours-deployer); an
   execution role with scoped logs, `s3:PutObject`/`GetObject` on the resume bucket, and
   `lambda:InvokeFunction` on its own ARN; an admin identity used only for setup and never in a
   `.env`. The execution role needs `ses:SendEmail`/`ses:SendRawEmail` (Resource `*`) for the
   auth email flow, and the sending domain (or a test inbox) must be a verified SES identity.
2. **Buckets.** New resume bucket in the same region as the Lambda; turn **all four** public-access-block
   flags on. New web bucket, private, with the OAC bucket policy pointing at the new distribution ARN.
3. **Copy the resume objects** from `career-tours-bkt`. Rows in the database hold S3 URLs, so
   either keep the object keys identical or plan a rewrite of the stored URLs.
4. **ECR + image.** Create the repository, then rebuild with
   `--platform linux/arm64 --provenance=false --sbom=false` — Lambda rejects the OCI index that
   Buildx attaches by default.
5. **Log group.** Either name the function to match the group the role policy allows, or fix both
   together. Getting this wrong produces a working function with no logs.
6. **Env map.** All 15 Lambda keys. Do **not** add `AWS_ACCESS_KEY`/`AWS_SECRET_KEY` (breaks the
   role fall-through) or `AWS_REGION` (rejected as reserved). Drop `DEEPINFRA_API_KEY`. Decide
   whether `SECRET_KEY` carries over (sessions survive) or is regenerated (everyone logs out).
7. **Front door.** HTTP API with `$default` route and stage — the `$default` stage serves paths
   with no stage prefix, which is what lets Mangum keep `api_gateway_base_path="/"`. CloudFront
   with the S3 default behaviour, an `/api/*` behaviour, the SPA-fallback function attached
   **viewer-request on the default behaviour**, and `CustomErrorResponses` **empty**.
8. **Certificate in us-east-1**, then Route53 A + AAAA aliases on apex and `www`.
9. **Verify** in this order: `GET /db-test` through the Function URL, then through CloudFront;
   a resume upload (proves the role's S3 grant); `POST .../generate?async=1` returning 202
   (proves self-invoke) and reaching a terminal job status; `GET /api/nope` returning **404 JSON**,
   not `200 text/html` (proves the SPA fallback is scoped correctly); a login (proves `SECRET_KEY`).

### Moving to a new database

1. Only five variables change — `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` — in
   both copies. Keep `DB_SSLMODE=require`.
2. Put it in the **same region as the Lambda**. At ~74 ms per round trip today, and with
   `services/matching/ranking.py` issuing one `get_skills()` query per occupation in a Python
   loop, cross-region latency is a multiplier on an N+1, not a constant.
3. Prefer the **pooled** endpoint if the provider offers one. Safe here: every repository is raw
   `text()` SQL plus `commit()`, with no `LISTEN`, advisory locks or server-side cursors.
4. Apply `backend/table_schemas/` in dependency order, then every script in
   `backend/migrations/`. Treat the schema files as approximate — they have drifted from the live
   database before; diff `pg_constraint` between old and new before trusting them.
5. Seed the catalog tables — `skills`, `courses`, `occupations`, `course_skills`,
   `occupation_skills`, plus the section-question corpus. Empty catalog tables do not error:
   `POST /generate` succeeds and returns zero matches, which the UI renders as
   "No Career Recommendations Yet". `skills` is a hard prerequisite for the two join tables.
   See [data-pipelines.md](data-pipelines.md).
6. The app's own role needs only DML and `SELECT`. Reserve the owner role for migrations and
   loaders instead of handing it to the runtime.
7. **Split local from production while you are here.** Point `.env` at a separate database so a
   local smoke test stops being a production write.
