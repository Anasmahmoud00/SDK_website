from narrative_ai.api.app import create_app

# Expose the app instance for Vercel Serverless/FastAPI deployment
app = create_app()
