# ForestGuard Frontend

React + Vite + Tailwind UI for ForestGuard.

## Requirements
- Node 18+ (for fetch in scripts)
- Backend running locally or a remote API URL

## Setup
1. From `frontend/`, install deps: `npm install`
2. Copy `.env.example` to `.env` and set `VITE_API_BASE_URL`
3. Start the backend (from repo root):
   - `uvicorn app.main:app --reload --port 8000`
   - or `docker-compose up -d`

## Run the frontend
`npm run dev`

## Backend health check
`npm run backend:health`

## Tests
`npm run test -- --run`
