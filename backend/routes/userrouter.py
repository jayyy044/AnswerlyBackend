from fastapi import APIRouter, Form, File, UploadFile
from pydantic import BaseModel
from typing import Optional
from controllers.userController import initializeAPIkeys, processUserData, getUserProfile, updateUserProfile


userRoutes = APIRouter()


class APIKeysRequest(BaseModel):
    geminiKey: str
    tavilyKey: str
    email: str


@userRoutes.post("/apikeys")
async def setApiKey(data: APIKeysRequest):
    return await initializeAPIkeys(data.model_dump())

@userRoutes.post('/userdata')
async def setUserData(linkedinText: str = Form(...),resume: UploadFile = File(...), email: str = Form(...)):
    return await processUserData(linkedinText, resume, email)

class userProfile(BaseModel):
    email: str

@userRoutes.post('/profile')
async def getProfile(data: userProfile):
    return await getUserProfile(data.model_dump())

@userRoutes.post('/update')
async def updateProfile(
    email: str = Form(...),
    updateLinkedin: bool = Form(...),
    updateResume: bool = Form(...),
    linkedinText: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None)
):
    return await updateUserProfile(
        email,
        updateLinkedin,
        updateResume,
        linkedinText,
        resume
    )
    



   
