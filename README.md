# wordpress-mcp-server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes WordPress site management as AI-callable tools. Enables AI assistants (Claude, Amazon Q, Google ADK agents, etc.) to create, read, update, and delete WordPress content through natural language.

## Features

- 6 MCP tools covering the full WordPress post lifecycle
- Auto-derives and assigns post categories using keyword extraction and fuzzy matching
- SSL-aware HTTP client with configurable certificate verification
- Supports `stdio` (local/MCP Inspector), `sse`, and `streamable-http` (Cloud Run) transports
- Deployable to Google Cloud Run via Cloud Build CI/CD pipeline

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_latest_posts` | Fetch the latest N posts (default 5), ordered by date |
| `fetch_posts` | Filter posts by search, status, author, category, tag, and pagination |
| `get_post_categories` | List all existing WordPress categories |
| `create_new_post` | Create a post with auto-derived category assignment |
| `update_existing_post` | Update title, content, or status of an existing post by ID |
| `delete_existing_post` | Delete a post by ID (move to trash or permanently delete) |

## Project Structure

```
wordpress-mcp-server/
├── src/wp-mcp/
│   ├── server.py        # FastMCP server and tool definitions
│   └── utils.py         # WordPress REST API helpers, category resolution
├── Dockerfile           # Cloud Run container (Python 3.14 + uv)
├── cloudbuild.yaml      # GCP Cloud Build CI/CD pipeline
├── pyproject.toml       # Project metadata and dependencies (Python >=3.14)
├── .env                 # Local credentials (not committed to git)
└── .dockerignore
```

## Prerequisites

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) package manager
- A WordPress site with REST API enabled (Settings → Permalinks → any non-Plain option)
- WordPress application password (Users → Profile → Application Passwords)

## Local Setup

**1. Clone and install dependencies**
```bash
git clone https://github.com/<your-username>/wordpress-mcp-server.git
cd wordpress-mcp-server
uv sync
```

**2. Configure environment**

Create a `.env` file at the project root:
```
WP_URL=https://your-wordpress-site.com
WP_USER=admin
WP_PASS=xxxx-xxxx-xxxx-xxxx
```

Optional — if your site uses a self-signed certificate:
```
WP_SSL_CERT=certs/wp-server.pem
```

**3. Run the MCP server**
```bash
uv run python src/wp-mcp/server.py
```

## Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run python src/wp-mcp/server.py
```

Open http://localhost:5173 — all 6 tools will be listed and directly invokable.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WP_URL` | Yes | WordPress site base URL (no trailing slash) |
| `WP_USER` | Yes | WordPress username |
| `WP_PASS` | Yes | WordPress application password |
| `WP_SSL_CERT` | No | Path to PEM cert file for self-signed certs. Defaults to system CAs (`True`) |
| `MCP_TRANSPORT` | No | `stdio` (default), `sse`, or `streamable-http` (required for Cloud Run) |
| `PORT` | No | HTTP port for `streamable-http` transport. Defaults to `8080` |

## Deploy to Google Cloud Run

### One-time GCP setup

```bash
# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# Create Artifact Registry repository
gcloud artifacts repositories create cloud-run-source-deploy \
  --repository-format=docker \
  --location=us-central1

# Store credentials in Secret Manager
echo -n "https://your-wordpress-site.com" | gcloud secrets create WP_URL --data-file=-
echo -n "admin" | gcloud secrets create WP_USER --data-file=-
echo -n "your-app-password" | gcloud secrets create WP_PASS --data-file=-

# Grant Cloud Build access to Secret Manager and Cloud Run
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<PROJECT_NUMBER>@cloudbuild.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<PROJECT_NUMBER>@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
```

### Initial Cloud Run service creation (run once before CI/CD)

```bash
gcloud run deploy wordpress-mcp-server \
  --image=us-central1-docker.pkg.dev/<PROJECT_ID>/cloud-run-source-deploy/wordpress-mcp-server/wordpress-mcp-server:latest \
  --region=us-central1 \
  --platform=managed \
  --no-allow-unauthenticated \
  --set-env-vars=MCP_TRANSPORT=streamable-http \
  --set-secrets=WP_URL=WP_URL:latest,WP_USER=WP_USER:latest,WP_PASS=WP_PASS:latest
```

### CI/CD via Cloud Build trigger

Connect your GitHub repo to a Cloud Build trigger (GCP Console → Cloud Build → Triggers → Create Trigger) pointing to `cloudbuild.yaml`. Set these substitution variables in the trigger:

| Variable | Value |
|----------|-------|
| `_DEPLOY_REGION` | `us-central1` |
| `_AR_HOSTNAME` | `us-central1-docker.pkg.dev` |
| `_AR_REPOSITORY` | `cloud-run-source-deploy` |
| `_AR_PROJECT_ID` | your GCP project ID |
| `_SERVICE_NAME` | `wordpress-mcp-server` |
| `_TRIGGER_ID` | your Cloud Build trigger ID |

Every `git push` to `main` will automatically build the Docker image, push to Artifact Registry, and deploy to Cloud Run.

### Manual build and deploy

```bash
gcloud builds submit --config cloudbuild.yaml
```

## Tech Stack

- [Python 3.14](https://www.python.org/)
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [httpx](https://www.python-httpx.org/) — async HTTP client for WordPress REST API
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment variable management
- [uv](https://docs.astral.sh/uv/) — fast Python package and project manager
- [Google Cloud Run](https://cloud.google.com/run) — serverless container hosting
- [Google Cloud Build](https://cloud.google.com/build) — CI/CD pipeline
- [Google Artifact Registry](https://cloud.google.com/artifact-registry) — Docker image storage
