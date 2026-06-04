# Team Handoff: Text to Zensical Docker Release

This runbook covers publishing and team deployment for Text to Zensical.

## Publisher Workflow (Recommended)

### 1) Update release version

Edit the `VERSION` file using semantic version format:

- `1.0.2` or `v1.0.2`

### 2) Commit and push to main

The GitHub Actions workflow publishes both:

- `ghcr.io/el-dragon-1/text-to-zensical:vX.Y.Z`
- `ghcr.io/el-dragon-1/text-to-zensical:latest`

The published image is multi-architecture:

- `linux/amd64`
- `linux/arm64`

### 3) Verify published image (optional)

```bash
docker buildx imagetools inspect ghcr.io/el-dragon-1/text-to-zensical:vX.Y.Z
```

## Publisher Workflow (Manual Fallback)

Use this only if GitHub Actions is unavailable.

```bash
cd /Users/davidpolizzi/Development/docker/text-to-zensical

export GH_OWNER=el-dragon-1
export IMAGE=ghcr.io/${GH_OWNER}/text-to-zensical
export TAG=vX.Y.Z

docker login ghcr.io
docker buildx build \
	--platform linux/amd64,linux/arm64 \
	-t "${IMAGE}:${TAG}" \
	-t "${IMAGE}:latest" \
	--push \
	.
```

## Team Consumer Workflow (Simple)

### Required files

- `docker-compose.release.yml`
- `.env` (copy from `.env.team.example`)

### 1) Create `.env`

```bash
cp .env.team.example .env
```

Update only these values if needed:

- `TEXT_TO_ZENSICAL_IMAGE=ghcr.io/el-dragon-1/text-to-zensical`
- `TEXT_TO_ZENSICAL_TAG=latest`
- `SECRET_KEY=<strong-random-secret>`
- `PORT=10253`

### 2) Start

```bash
docker compose -f docker-compose.release.yml up -d
```

### 3) Validate

```bash
docker compose -f docker-compose.release.yml ps
curl -I http://localhost:10253
```

Open in browser:

- `http://localhost:10253`

### 4) Stop

```bash
docker compose -f docker-compose.release.yml down
```

## One-Command Option For Non-Technical Users

If you distribute a folder where `docker-compose.release.yml` is renamed to `docker-compose.yml`, users can run:

```bash
docker compose up -d
```

## Persistence Across Upgrades

Project data is persisted on the host in `./exports` via a bind mount. Updating image tags does not remove existing data as long as the same deployment folder and mount path are retained.

## Release Practice

- `latest` is easiest for non-technical users.
- Pin explicit tags (`vX.Y.Z`) for controlled rollouts and rollback.
