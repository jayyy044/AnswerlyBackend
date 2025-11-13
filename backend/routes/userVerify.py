from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def verifyUser(request: Request, call_next):
    
    public_paths = ["/"]
    if request.url.path in public_paths:
        response = await call_next(request)
        return response
    

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        print("----Missing Authorization header----")
        return JSONResponse(
            status_code=401,
            content={"error": "Missing Authorization header"},
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        # Use Supabase's get_user() to verify the token
        user = supabase.auth.get_user(token)
        print(f"User Metadata: {user.user.user_metadata}")
        request.state.user = user
    except Exception as e:
        print(f"Authorization Error: {e}")
        print("----User Authorization Failed----")
        return JSONResponse(
            status_code=401,
            content={"error": "User Authorization Failed"},
        )
    
    response = await call_next(request)
    return response