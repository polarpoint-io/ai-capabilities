# @polarpoint/agentsmd-validator

Validates `AGENTS.md` files against a zone-structured schema. Designed for use in CI pipelines across platform engineering repos.

## Usage

```bash
npx @polarpoint/agentsmd-validator \
  --schema https://raw.githubusercontent.com/your-org/platform-standards/main/schema.json \
  --file AGENTS.md
```

### Options

| Flag | Description |
|---|---|
| `--file <path>` | Path to the AGENTS.md file to validate (required) |
| `--schema <url\|path>` | URL or local path to a schema.json (optional) |
| `--strict` | Treat warnings as errors (non-zero exit) |

## What it checks

1. **Zone markers present** — `<!-- zone:1:start -->` / `<!-- zone:1:end -->` exist
2. **Zone order** — zones appear in ascending numeric order
3. **Required Zone 1 sections** — `## Sync model`, `## Forbidden paths`, `## Naming conventions`, `## Running tests` all present
4. **Running tests is actionable** — the section contains at least one executable command (code block or inline command)
5. **Zone 1 hash** — if a schema is supplied, warns when Zone 1 content has drifted from the template version

## Zone structure

```markdown
<!-- zone:1:start -->
## Sync model
...
## Forbidden paths
...
## Naming conventions
...
## Running tests
...
<!-- zone:1:end -->

<!-- zone:2:start -->
## Team conventions
...
<!-- zone:2:end -->

<!-- zone:3:start -->
## Repo-specific notes
...
<!-- zone:3:end -->
```

## GitHub Actions

Copy `.github/workflows/validate-agents-md.yml` into your repo, update the `--schema` URL to point at your `platform-standards` repo, and the validator runs on every PR that touches `AGENTS.md`.

## Schema format

```json
{
  "templateVersion": "1.0.0",
  "zone1Hash": "98dfe660cbdaf240",
  "requiredSections": ["Sync model", "Forbidden paths", "Naming conventions", "Running tests"]
}
```

After editing your template, regenerate `zone1Hash`:

```bash
node -e "
  const c=require('crypto'), f=require('fs');
  const z=f.readFileSync('templates/default-agents-md.md','utf8')
    .match(/zone:1:start[\s\S]*?zone:1:end/)[0];
  console.log(c.createHash('sha256').update(z.replace(/\s+/g,' ').trim()).digest('hex').slice(0,16))
"
```
