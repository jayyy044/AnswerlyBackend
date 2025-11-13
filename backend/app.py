from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from routes.userrouter import userRoutes
from routes.jobrouter import jobRoutes
from routes.userVerify import verifyUser
# Import your dependency getters
from services.dependencies import getEmbeddingConfig, getSupabaseClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ Server starting up...")
    
    # Initialize all your global instances on startup
    try:
        getEmbeddingConfig()  # Initialize Voyage embeddings
        getSupabaseClient()  # Initialize Supabase
        print("✅ All services initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        raise
    
    yield
    
    print("🛑 Server shutting down...")
    # Clean up if needed (close connections, etc.)

# Create app with lifespan manager
app = FastAPI(
    title="LLM Backend",
    description="Backend for managing LLM pipeline and user interactions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS setup (React frontend)
origins = [
    "http://localhost:4000",
    "https://your-production-frontend.netlify.app",  # Update with real URL
    "http://18.222.21.94:8000",  # Your EC2 IP
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(verifyUser)

# Register routes
app.include_router(userRoutes, prefix="/user", tags=["User"])
app.include_router(jobRoutes, prefix="/job", tags=["Job"])


@app.get("/")
async def root():
    return {"message": "FastAPI server running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)