import './ExperienceForm.css'
import { toast } from "react-toastify"
import { useAuth } from "../context/AuthContext"
import { useState, useRef } from "react"
import { supabase } from '../context/supabaseClient'
import CircularProgress from '@mui/material/CircularProgress';     

const ExperienceForm = () => {
  const [uploadedFile, setUploadedFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [linkedinText, setLinkedinText] = useState("")
  const fileInputRef = useRef(null)
  const { session } = useAuth();
  const [loading, setLoading] = useState(false)



  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file && file.type === "application/pdf") {
      setUploadedFile(file);
    } else {
      alert("Only PDF files are allowed.");
      e.target.value = null;
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type === "application/pdf") {
      setUploadedFile(file);
    } else {
      alert("Only PDF files are allowed.");
    }
  };

  const handleRemoveFile = () => {
    setUploadedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + " B"
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB"
    return (bytes / (1024 * 1024)).toFixed(1) + " MB"
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate that both fields are filled
    if (!linkedinText.trim() || !uploadedFile) {
      toast.warn("Please fill in both fields.");
      return;
    }
    setLoading(true);

    // Prepare the data for backend
    const formData = new FormData();
    formData.append('linkedinText', linkedinText);
    formData.append('resume', uploadedFile);
    formData.append('email', session?.user?.email)
    console.log("Data ready to send:");
    console.log("LinkedIn Text:", linkedinText.length);
    console.log("File Name:", uploadedFile.name);
    console.log("Email:", session?.user?.email);


    try{
      const response = await fetch('/api/user/userdata', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session?.access_token}`
        },
        body: formData
      });
      const respData = await response.json();
      if(!response.ok){
        console.error("An error occured while trying to save user data: ", respData.error);
        toast.error("Failed to save user data");
        return;
      }

      console.log("Success: ",respData.message)
      const { data, error } = await supabase.auth.updateUser({
      data: { experienceData: true },
      });
      if (error) {
        console.error('Error updating user metadata:', error);
        toast.error("Failed to save user data");
        return;
      } 
      console.log('User metadata updated successfully:', data);
      setLoading(false);
      
      window.location.reload();
    }
    catch(error){
      console.error('Error:', error);
      toast.error("Failed to save user data");
      return
    }
  };
  
  return (
    <div className="userDataForm">
        <form className="userformcont" onSubmit={handleSubmit}>
            <div className="userformtitle">
                <h1>Share Your Information to <span>Get Started</span></h1>
            </div>
            <div className="form-section">
                <div className="file-upload-header">
                    <h2 className="file-upload-title">Copy Past Linkedin Here</h2>
                </div>
                <textarea
                    className="text-area"
                    placeholder="Type your text here..."
                    rows={8}
                    value={linkedinText}
                    onChange={(e) => setLinkedinText(e.target.value)}
                />
            </div>

            <div className="form-section">
                <div className="file-upload-header">
                    <h2 className="file-upload-title">Upload Resume</h2>
                </div>

                {!uploadedFile && (
                <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`upload-area ${isDragging ? "upload-area-dragging" : ""}`}
                >
                    <svg
                    className="upload-icon"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                    >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                    </svg>
                    <p className="upload-text">Upload your file here</p>
                    <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="file-input-hidden"
                    />
                </div>
                )}

                {!uploadedFile && <p className="file-size-info">Maximum size: 30MB</p>}

                {uploadedFile && (
                <div className="file-card">
                    <div className="file-icon-container">
                    <svg
                        className="file-icon"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                    </svg>
                    </div>
                    <div className="file-info">
                    <p className="file-name">{uploadedFile.name}</p>
                    <p className="file-size">{formatFileSize(uploadedFile.size)}</p>
                    </div>
                    <button type="button" onClick={handleRemoveFile} className="delete-button">
                    <svg
                        className="delete-icon"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                    </svg>
                    <span className="sr-only">Remove file</span>
                    </button>
                </div>
                )} 
            </div>
            <button type='submit' className="useformsubmit" disabled={loading}>
              {loading ? <CircularProgress size="25px" color="white" className='loader'/> : 'Submit'}</button>
        </form>
    </div>
  )
}

export default ExperienceForm