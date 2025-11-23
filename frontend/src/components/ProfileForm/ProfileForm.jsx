import React from 'react'
import './ProfileForm.css'
import { useEffect, useState, useRef } from 'react'
import { useAuth } from "../context/AuthContext"
import { toast } from 'react-toastify'
import CircularProgress from '@mui/material/CircularProgress'

const ProfileForm = () => {
    const { session } = useAuth();
    const [loading, setLoading] = useState(false)
    const [profileData, setProfileData] = useState({
        linkedinText: '',
        resume: null,
        resumeFilename: null,
        email: session?.user?.email
    });
    const [originalData, setOriginalData] = useState({
        linkedinText: '',
        resume: null,
        resumeFilename: null,
        email: session?.user?.email
    });
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef(null);

    useEffect(() => {
        const fetchProfileData = async () => {
            setLoading(true);
            try{
                const response = await fetch('/api/user/profile', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${session?.access_token}`
                    },
                    body: JSON.stringify({ email: session?.user?.email }),
                });
                const data = await response.json();
                if (!response.ok) {
                    console.error("An error occured while trying to get profile data: ", data.error);
                    toast.error("Failed to get profile data");
                    return;
                }
                let resumeFile = null;
                if (data.resumeBase64 && data.resumeFilename) {
                    resumeFile = base64ToFile(data.resumeBase64, data.resumeFilename, 'application/pdf');
                }

                const loadedData = {
                    linkedinText: data.linkedinText || '',
                    resume: resumeFile,
                    resumeFilename: data.resumeFilename,
                };

                // ✅ Set both current and original data
                setProfileData({
                    ...loadedData,
                    email: session?.user?.email
                });
                
                setOriginalData(loadedData);

                console.log("Profile data state updated"); // ✅ Add debug
                setLoading(false);

            }
            catch(err){
                console.error("Failed to get profile data: ",err);
                toast.error("Failed to get profile data");
            }
        };        
        
        // ✅ Only fetch when session is available
        if (session?.user?.email && session?.access_token) {
            fetchProfileData(); 
        }
    }, [session]);
    
    // ✅ Add session as dependency
    const base64ToFile = (base64String, filename, mimeType) => {
        try {
            // Decode base64 string
            const byteCharacters = atob(base64String);
            const byteNumbers = new Array(byteCharacters.length);
            
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: mimeType });
            
            // Create File from Blob
            return new File([blob], filename, { type: mimeType });
        } catch (error) {
            console.error("Error converting base64 to file:", error);
            return null;
        }
    }

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file && file.type === "application/pdf") {
            setProfileData({
                ...profileData,
                resume: file,
                resumeFilename: file.name
            });
        } else {
            alert("Only PDF files are allowed.");
            e.target.value = null;
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file && file.type === "application/pdf") {
            setProfileData({
                ...profileData,
                resume: file,
                resumeFilename: file.name
            });
        } else {
            alert("Only PDF files are allowed.");
        }
    };

    const handleRemoveFile = () => {
        setProfileData({
            ...profileData,
            resume: null,
            resumeFilename: null
        });
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const handleProfileUpdate = async (e) => {
        e.preventDefault();
        const linkedinChanged = originalData.linkedinText !== profileData.linkedinText;
        const resumeChanged = originalData.resumeFilename !== profileData.resumeFilename;

        // If nothing changed, show error
        if (!linkedinChanged && !resumeChanged) {
            toast.error("No profile updates were made");
            return;
        }

        // If resume removed but no LinkedIn change = no actual update
        if (!linkedinChanged && !profileData.resume) {
            toast.error("No profile updates were made");
            return;
        }
        setLoading(true);


        const formData = new FormData();
        formData.append('email', session?.user?.email);
        formData.append('updateLinkedin', linkedinChanged);
        formData.append('updateResume', resumeChanged);

        if( linkedinChanged && (resumeChanged && profileData.resume)){
            formData.append('linkedinText', profileData.linkedinText);
            formData.append('resume', profileData.resume);

        }

        // Only append the fields that changed
        else if (linkedinChanged) {
            formData.append('linkedinText', profileData.linkedinText);
            formData.append('resume', null)
        }

        else if (resumeChanged && profileData.resume) { // ✅ Only if there's actually a new resume
            formData.append('resume', profileData.resume);
            formData.append('linkedinText', null)
        }

        try {
            const response = await fetch('/api/user/update', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${session?.access_token}`
                },
                body: formData,
            });
            const data = await response.json();
            if (!response.ok){
                console.error("An error occured while trying to update profile: ", data.error);
                toast.error("Failed to update profile");
                return;
            }
            console.log("Profile updated successfully");
            toast.success("Profile updated successfully");
            setOriginalData(profileData);
            setLoading(false);

        }
        catch(err){
            console.error("Failed to update profile: ",err);
            toast.error("Failed to update profile");
            
        }
    };





    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    };








  return (
        <form className="profileformcont" onSubmit={handleProfileUpdate}>
            <h1>Update your <span>Profile</span></h1>
            <div className="pfSection">
                <div >
                    <h2>Your Current Linkedin Profile</h2>
                </div>
                <textarea 
                    className="pf-ta"
                    value={profileData.linkedinText}
                    onChange={(e) => setProfileData({...profileData, linkedinText: e.target.value})}
                    rows={10}
                />
            </div>
            <div className="pfSection">
                <div >
                    <h2>Your Current Resume</h2>
                </div>

                 {!profileData.resume && (
                    <div
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                        className={`pf-upload-area ${isDragging ? "pf-upload-area-dragging" : ""}`}
                    >
                        <svg
                            className="pf-upload-icon"
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
                        <p className="pf-upload-text">Upload your file here</p>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".pdf"
                            onChange={handleFileChange}
                            className="file-input-hidden"
                        />
                    </div>
                )}

                {!profileData.resume && <p className="pf-file-size-info">Maximum size: 30MB</p>}
                {profileData.resume && (
                    <div className="pf-file-card">
                        <div className="pf-file-icon-container">
                            <svg
                                className="pf-file-icon"
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
                        <div className="pf-file-info">
                            <p className="pf-file-name">{profileData.resumeFilename}</p>
                            <p className="pf-file-size">{formatFileSize(profileData.resume.size)}</p>
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
                
                
                <button type="submit" className="profileformsubmit" disabled={loading}>
                    {loading ? <CircularProgress size="25px" color="secondary" className='loader'/> : 'Update Profile'}</button>

            </div>
            

        </form>
  )
}

export default ProfileForm