# Public Deployment

Recommended first public setup:

```text
Local collector on this Mac
→ public/data/items.json is refreshed
→ GitHub repository receives the updated static site
→ Cloudflare Pages publishes the public website
```

## Build The Public Site

```bash
cd /Users/oh/Documents/Codex/2026-05-16/new-chat/agri-info-hub
./scripts/build_static_site.sh
```

The deployable site is generated in:

```text
public/
```

Cloudflare Pages should use `public` as the output directory.

## Prepare Git

```bash
cd /Users/oh/Documents/Codex/2026-05-16/new-chat/agri-info-hub
./scripts/publish_static_git.sh "Initial public site"
```

Then create an empty GitHub repository in the browser and connect it:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_NAME/agri-info-hub.git
git push -u origin main
```

## Cloudflare Pages Settings

Use these settings when connecting the GitHub repository:

```text
Framework preset: None
Build command: ./scripts/build_static_site.sh
Build output directory: public
```

## Updating Data

The collector still runs every 30 minutes on this Mac. To publish the latest generated data publicly, run:

```bash
./scripts/publish_static_git.sh "Update agriculture data"
git push
```

The next improvement is to let `launchd` run this publish step automatically after collection, but it needs a GitHub credential/token configured first.

## Automatic Updates From This Mac

Create a GitHub fine-grained token:

```text
Repository access: oheus/agri-info-hub
Permission: Contents = Read and write
```

Save it locally:

```bash
./scripts/setup_github_token.sh
```

Reinstall the LaunchAgent so each collection cycle also publishes JSON updates:

```bash
./scripts/install_launchd.sh
```

The token is stored outside the repository at:

```text
~/.agri-info-hub/github.env
```
