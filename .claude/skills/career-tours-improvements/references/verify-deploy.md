# Verifying and deploying

There is **no test suite, no linter and no CI**. `npm run build` is the only automated
gate, so verification is explicit and manual. Do not report a phase done without it.

## Frontend

```bash
cd frontend && npm run build     # the only automated gate
```

After any style or token change, grep for stragglers — deleted tokens fail silently in
Tailwind (the class just compiles to nothing):

```bash
cd frontend/src
grep -rn "text-gradient\|surface-glass\|app-aura\|btn-success\|accent-\|rounded-2xl\|rounded-3xl\|shadow-glass\|animate-float\|animate-pulse-slow\|orbTone\|eyebrowTone\|iconTone\|radius=\|blur-3xl\|bg-gradient\|font-extrabold\|levelTone" .
```

Then check for lucide imports left dangling by a removed icon:

```bash
python3 - <<'PY'
import re, pathlib
for p in sorted(pathlib.Path('src').rglob('*.jsx')):
    s = p.read_text()
    m = re.search(r"import \{([^}]*)\} from 'lucide-react'", s)
    if not m: continue
    body = s[m.end():]
    dead = [n.strip() for n in m.group(1).split(',')
            if n.strip() and not re.search(r'\b'+re.escape(n.strip())+r'\b', body)]
    if dead: print(f"DEAD IMPORT {p}: {', '.join(dead)}")
PY
```

## In the browser (Playwright MCP)

Look at the real deployed app, in **light and dark**, at **1440px and 390px**. A useful
assertion that the effect layer stayed dead — run it via `browser_evaluate`:

```js
() => {
  const all = [...document.querySelectorAll('*')];
  return {
    blur: all.filter(el => getComputedStyle(el).backdropFilter !== 'none').length,      // expect 0
    gradients: all.filter(el => getComputedStyle(el).backgroundImage.includes('gradient')).length, // expect 0
    radii: [...new Set(all.map(el => getComputedStyle(el).borderRadius).filter(r => r !== '0px'))],
  };
}
```

Also check: forced-colors (devtools emulation — panels must be opaque with visible
borders and focus rings), `prefers-reduced-motion`, and one keyboard-only pass over the
careers list (arrow/Enter/Space, visible focus ring, correct announcement).

## Auth (re-run after touching any route)

```bash
D=https://nipunacareers.com
# Unauthenticated must be 401 everywhere except auth/health:
curl -s -o /dev/null -w "%{http_code}\n" $D/api/students/<uuid>
curl -s -o /dev/null -w "%{http_code}\n" $D/api/recommendations/projects/<id>
# Cross-account must be 404 (never 200 or 403):
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_B" $D/api/projects/<A-project>
# Still public:
curl -s -o /dev/null -w "%{http_code}\n" -X POST $D/api/auth/login -H 'Content-Type: application/json' -d '{"email":"x@y.z","password":"no"}'   # 401 for bad creds
```

To test cross-account, register two throwaway accounts on `@example.invalid`, then
**delete them afterwards**:

```sql
DELETE FROM students WHERE email LIKE '%@example.invalid';
```

## Deploy

Backend is a container image; frontend is static objects in S3. Full flags and the
reasons they are mandatory are in [docs/architecture.md](../../../../docs/architecture.md).

```bash
# backend — arm64, and the three attestation flags are required or Lambda rejects the manifest
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS --password-stdin 307857432997.dkr.ecr.ap-south-1.amazonaws.com
docker buildx build --platform linux/arm64 --provenance=false --sbom=false \
  --output type=image,oci-mediatypes=false,push=true \
  -t 307857432997.dkr.ecr.ap-south-1.amazonaws.com/career-tours-api:latest .
aws lambda update-function-code --function-name career-tours-api --region ap-south-1 \
  --image-uri 307857432997.dkr.ecr.ap-south-1.amazonaws.com/career-tours-api:latest
aws lambda wait function-updated --function-name career-tours-api --region ap-south-1

# frontend — hashed assets cache forever, index.html never
cd frontend && npm run build && cd ..
aws s3 sync frontend/dist/ s3://career-tours-web/ --delete --exclude index.html \
  --cache-control "public,max-age=31536000,immutable"
aws s3 cp frontend/dist/index.html s3://career-tours-web/index.html \
  --cache-control "no-store" --content-type "text/html"
aws cloudfront create-invalidation --distribution-id E1TW6HR68G4A7T --paths "/index.html"
```

Apply any new migration **before** updating the function code. Postgres is on Neon,
reachable from anywhere, so apply it directly. Note this hits the same database local
development uses, so the schema change lands everywhere at once:

```bash
set -a; . .env; set +a
PGPASSWORD="$DB_PASSWORD" PGSSLMODE="${DB_SSLMODE:-require}" \
  psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  -v ON_ERROR_STOP=1 --single-transaction -f backend/migrations/00N_*.sql
```

Post-deploy smoke test:

```bash
D=https://nipunacareers.com
curl -s -o /dev/null -w "site:%{http_code}\n" $D/
curl -s $D/api/db-test                  # {"database":"neondb"}
# note the log-group override — the default /aws/lambda/career-tours-api is empty
aws logs tail /aws/lambda/career-tours-lambda --region ap-south-1 --since 15m
```

For complex SQL or JSON payloads, write the file locally and `scp` it — heredocs with
`$$`, quotes or `{`/`}` get mangled by shell escaping.
