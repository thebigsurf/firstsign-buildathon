#!/usr/bin/env bash
# Deploys FirstSign to Cloud Run (asia-south1). Needs: gcloud signed in (gcloud auth login) and billing on the project.
# Usage (from anywhere):  bash infra/deploy.sh
# The Gemini key is read from .env and sent to Secret Manager over stdin; it is never printed or written elsewhere.
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-firstsign-buildathon}"
REGION="${GOOGLE_CLOUD_REGION:-asia-south1}"
SERVICE="firstsign"
REPO="firstsign"
SECRET="gemini-api-key"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:latest"

GCLOUD="$(command -v gcloud || true)"
if [ -z "$GCLOUD" ] && [ -n "${LOCALAPPDATA:-}" ]; then
  GCLOUD="$(cygpath -u "$LOCALAPPDATA" 2>/dev/null || echo "$LOCALAPPDATA")/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
fi
# Windows: cmd.exe mangles a .cmd path with spaces when arguments also contain spaces, so use the 8.3 short path.
if [ -f "$GCLOUD" ] && command -v cygpath >/dev/null 2>&1 && [[ "$GCLOUD" == *" "* ]]; then GCLOUD="$(cygpath -u "$(cygpath -s -w "$GCLOUD")")"; fi
[ -f "$GCLOUD" ] || { echo "gcloud not found. Install the Google Cloud SDK first." >&2; exit 1; }
g() { "$GCLOUD" "$@"; }

ACCOUNT="$(g auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null || true)"
[ -n "$ACCOUNT" ] || { echo "gcloud is not signed in. Run: gcloud auth login" >&2; exit 1; }
BILLING="$(g billing projects describe "$PROJECT" --format='value(billingEnabled)' 2>/dev/null || true)"
[ "$BILLING" = "True" ] || { echo "Billing is not enabled on project $PROJECT. Link a billing account in the Cloud console." >&2; exit 1; }

echo "Project $PROJECT, region $REGION, account $ACCOUNT"
g config set project "$PROJECT" >/dev/null

echo "Enabling APIs..."
g services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

echo "Preparing Artifact Registry..."
g artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 \
  || g artifacts repositories create "$REPO" --repository-format=docker --location "$REGION" --description "FirstSign images"

echo "Storing GEMINI_API_KEY in Secret Manager..."
KEY="$(grep -E '^GEMINI_API_KEY=' "$ROOT/.env" | head -n1 | cut -d= -f2- | tr -d '\r"'"'" )"
[ -n "$KEY" ] || { echo "GEMINI_API_KEY is empty in $ROOT/.env" >&2; exit 1; }
if g secrets describe "$SECRET" >/dev/null 2>&1; then
  printf %s "$KEY" | g secrets versions add "$SECRET" --data-file=- >/dev/null
else
  printf %s "$KEY" | g secrets create "$SECRET" --replication-policy=automatic --data-file=- >/dev/null
fi
unset KEY

PROJECT_NUMBER="$(g projects describe "$PROJECT" --format='value(projectNumber)')"
g secrets add-iam-policy-binding "$SECRET" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor >/dev/null

echo "Building image with Cloud Build..."
(cd "$ROOT" && g builds submit --config infra/cloudbuild.yaml --substitutions "_IMAGE=${IMAGE}" .)

echo "Deploying to Cloud Run..."
g run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 1 
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --set-secrets "GEMINI_API_KEY=${SECRET}:latest" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_REGION=${REGION},ALLOW_DEMO_RESET=0"

URL="$(g run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "Live URL: $URL"
curl -fsS "$URL/api/health" && echo
