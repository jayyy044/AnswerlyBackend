from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from routes.userrouter import userRoutes
from routes.jobrouter import jobRoutes
from routes.userVerify import verifyUser


# New lifespan context replaces startup/shutdown decorators
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ Server starting up...")
    # e.g., connect to database, load models, etc.
    yield
    print("🛑 Server shutting down...")
    # e.g., close DB connection, free resources, etc.

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
    "https://your-production-frontend.netlify.app"
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
