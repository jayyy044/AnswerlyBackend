from controllers.jobController import generateAnswer
from fastapi import APIRouter, Form, File, UploadFile
from pydantic import BaseModel

jobRoutes = APIRouter()


class JobDataRequest(BaseModel):
    jobTitle: str
    companyName: str
    question: str
    jobDescription: str
    email: str
@jobRoutes.post("/answer")
async def getJobResponse(data: JobDataRequest):
    return await generateAnswer(data.model_dump())