#!/usr/bin/env bash
# Deploys the Hyper-Context Engine backend (FastAPI) and frontend (Streamlit)
# to Cloud Run as two separate services.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (`gcloud auth login`)
#   - GOOGLE_CLOUD_PROJECT set in .env (the GCP project to deploy into)
#   - Elastic + Gemini credentials populated in .env (see .env.example)
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT in .env}"
REGION="${REGION:-us-central1}"
BACKEND_SERVICE="hyper-context-backend"
FRONTEND_SERVICE="hyper-context-frontend"

echo "Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com \
  --project="${PROJECT_ID}"

# Build a comma-separated KEY=VALUE list for --set-env-vars, skipping
# unset/empty vars so we never pass blank secrets to Cloud Run.
ENV_VARS=""
add_env_var() {
  local key="$1" val="$2"
  if [ -n "$val" ]; then
    ENV_VARS="${ENV_VARS:+${ENV_VARS},}${key}=${val}"
  fi
}
add_env_var ELASTIC_URL "${ELASTIC_URL:-}"
add_env_var ELASTIC_API_KEY "${ELASTIC_API_KEY:-}"
add_env_var ELASTIC_CLOUD_ID "${ELASTIC_CLOUD_ID:-}"
add_env_var GOOGLE_API_KEY "${GOOGLE_API_KEY:-}"
add_env_var GOOGLE_CLOUD_PROJECT "${GOOGLE_CLOUD_PROJECT:-}"
add_env_var GOOGLE_GENAI_USE_VERTEXAI "${GOOGLE_GENAI_USE_VERTEXAI:-}"

# --- 1. Backend ---------------------------------------------------------------
echo "Building backend image..."
gcloud builds submit . --tag "gcr.io/${PROJECT_ID}/${BACKEND_SERVICE}" \
  -f deploy/Dockerfile.backend --project="${PROJECT_ID}"

echo "Deploying backend..."
gcloud run deploy "${BACKEND_SERVICE}" \
  --image "gcr.io/${PROJECT_ID}/${BACKEND_SERVICE}" \
  --region "${REGION}" --project="${PROJECT_ID}" \
  --platform managed --allow-unauthenticated \
  --set-env-vars "${ENV_VARS}"

BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
  --region "${REGION}" --project="${PROJECT_ID}" --format 'value(status.url)')
echo "Backend deployed: ${BACKEND_URL}"

# --- 2. Frontend ----------------------------------------------------------------
echo "Building frontend image..."
gcloud builds submit . --tag "gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE}" \
  -f deploy/Dockerfile.frontend --project="${PROJECT_ID}"

echo "Deploying frontend..."
gcloud run deploy "${FRONTEND_SERVICE}" \
  --image "gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE}" \
  --region "${REGION}" --project="${PROJECT_ID}" \
  --platform managed --allow-unauthenticated \
  --set-env-vars "${ENV_VARS},BACKEND_URL=${BACKEND_URL}"

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
  --region "${REGION}" --project="${PROJECT_ID}" --format 'value(status.url)')
echo "Frontend deployed: ${FRONTEND_URL}"

# --- 3. Restrict backend CORS to the frontend's URL -----------------------------
echo "Updating backend CORS to allow ${FRONTEND_URL}..."
gcloud run services update "${BACKEND_SERVICE}" \
  --region "${REGION}" --project="${PROJECT_ID}" \
  --update-env-vars "FRONTEND_URL=${FRONTEND_URL}"

echo ""
echo "Done."
echo "  Backend:  ${BACKEND_URL}  (health: ${BACKEND_URL}/health)"
echo "  Frontend: ${FRONTEND_URL}"
