# Team Handoff: Text to Zensical Docker Release

This runbook is for publishing and consuming the Text to Zensical container image.

## Publisher Workflow (Build + Push)

### 1) Set release variables

```bash
cd /Users/davidpolizzi/Development/docker/text-to-zensical

export GH_OWNER=<your-org-or-user>
export IMAGE=ghcr.io/${GH_OWNER}/text-to-zensical
export TAG=v1.0.0
```

### 2) Authenticate to GHCR

```bash
# Option A: interactive

docker login ghcr.io

# Option B: token from env var
# export GHCR_USER=<github-username>
# export GHCR_TOKEN=<github-personal-access-token-with-package-write>
# echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
```

### 3) Build and push

```bash
docker build -t "$IMAGE:$TAG" -t "$IMAGE:latest" .
docker push "$IMAGE:$TAG"
docker push "$IMAGE:latest"
```

### 4) Verify published tags

```bash
docker pull "$IMAGE:$TAG"
docker pull "$IMAGE:latest"
```

## Team Consumer Workflow (Pull + Run)

### 1) Get runtime files

Required files:
- docker-compose.release.yml
- .env.team.example (copy to .env)

### 2) Configure env

```bash
cp .env.team.example .env
```

Edit .env:
- TEXT_TO_ZENSICAL_IMAGE=ghcr.io/<owner>/text-to-zensical
- TEXT_TO_ZENSICAL_TAG=v1.0.0
- SECRET_KEY=<strong-random-secret>
- PORT=10253 (or your preferred host port)

### 3) Start service

```bash
docker compose -f docker-compose.release.yml up -d
```

### 4) Validate

```bash
docker compose -f docker-compose.release.yml ps
curl -I http://localhost:10253
```

Open in browser:
- http://localhost:10253

### 5) Stop/update

```bash
docker compose -f docker-compose.release.yml down

# Update to a new image tag:
# 1) edit .env TEXT_TO_ZENSICAL_TAG
# 2) docker compose -f docker-compose.release.yml up -d
```

## Recommended Release Practice

- Use immutable version tags for production (v1.0.0, v1.0.1, etc).
- Keep latest as convenience only.
- Pin TEXT_TO_ZENSICAL_TAG in team .env files to avoid unplanned changes.
