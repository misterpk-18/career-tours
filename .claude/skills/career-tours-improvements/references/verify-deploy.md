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
D=https://career-tours.duckdns.org
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

The instance has neither Git nor Node, so push from a workstation:

```bash
cd frontend && npm run build && cd ..
K=~/Downloads/career_tours_key_pair.pem
H=ec2-user@13.203.206.148

# backend — never sync uploads/ (server-owned user data) or the venv/.env
rsync -az --delete -e "ssh -i $K" \
  --exclude __pycache__ --exclude '*.pyc' --exclude uploads \
  backend/ $H:/home/ec2-user/career-tours/backend/

rsync -az --delete -e "ssh -i $K" frontend/dist/ $H:/home/ec2-user/career-tours/frontend/dist/
rsync -az -e "ssh -i $K" docs README.md requirements.txt $H:/home/ec2-user/career-tours/

ssh -i $K $H 'sudo systemctl restart career-tours && sleep 7 && systemctl is-active career-tours'
```

Apply any new migration **before** the restart:

```bash
scp -i $K backend/migrations/00N_*.sql $H:/tmp/
ssh -i $K $H 'PGPASSWORD=$(grep ^DB_PASSWORD /home/ec2-user/career-tours/.env | cut -d= -f2) \
  psql -h 127.0.0.1 -U manojtungala -d career_tours -f /tmp/00N_*.sql'
```

Post-deploy smoke test:

```bash
D=https://career-tours.duckdns.org
curl -s -o /dev/null -w "site:%{http_code}\n" $D/
curl -s $D/db-test                      # {"database":"career_tours"}
ssh -i $K $H 'tail -20 /var/log/career-tours/error.log'
```

For complex SQL or JSON payloads, write the file locally and `scp` it — heredocs with
`$$`, quotes or `{`/`}` get mangled by shell escaping.
