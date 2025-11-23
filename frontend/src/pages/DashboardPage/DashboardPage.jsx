import React, { useEffect, useState,  } from 'react'
import { useAuth } from '../../components/context/AuthContext'
import ApiKeyForm from '../../components/ApiKeyForm/ApiKeyForm'
import './DashboardPage.css'
import GlassCard from '../../components/GlassCard/GlassCard'
import logoImg from '../../assets/answerLylogoV2.png'
import ExperienceForm from '../../components/ExperienceForm/ExperienceForm'
import { IoCopyOutline } from "react-icons/io5";
import { RiChatNewLine } from "react-icons/ri";
import { toast } from 'react-toastify'
import Tooltip from '@mui/material/Tooltip';
import { PiUserCircleThin } from "react-icons/pi";
import ProfileForm from '../../components/ProfileForm/ProfileForm'
import CircularProgress from '@mui/material/CircularProgress'
import LinearProgress from '@mui/material/LinearProgress';
import { supabase } from '../../components/context/supabaseClient'


const DashboardPage = () => {
    
    const { session, signOut } = useAuth();
    const [apiForm , setApiForm] = useState(false)
    const [experienceData, setExperienceData] = useState(false)
    const [questionAnswer, setQuestionAnswer] = useState("");
    const [profile, setProfile] = useState(false);
    const [loading, setLoading] = useState(false);
    

    useEffect(() => {
        if (!session?.user?.user_metadata?.geminiKey || !session?.user?.user_metadata?.tavilyKey) {
            setApiForm(true);
        } 
        if(!session?.user?.user_metadata?.experienceData){
            setExperienceData(true)
        }
    }, [session]);

    const [jobInfo, setJobInfo] = useState({
        jobTitle: '',
        companyName: '',
        question: '',
        jobDescription: '',
        email: session?.user?.email 
    });
    
    const handleJobData = async (e) => {
        e.preventDefault();

        if (!jobInfo.jobTitle || !jobInfo.companyName || !jobInfo.question || !jobInfo.jobDescription) {
            toast.error("Please fill in all fields");
            return;
        }
        setLoading(true);
        try{
            const response = await fetch('/api/job/answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token}`
                },
                body: JSON.stringify(jobInfo),
            });
            const respData = await response.json();
            if(!response.ok){
                console.error("An error occured while trying to get job answer: ", respData.error);
                toast.error("Failed to generate answer");
                return;
            }
            console.log("Success: ",respData.message)
            setQuestionAnswer(respData.finalResponse);
            const { data, error } = await supabase.auth.updateUser({
                data: { numberOfRequest: 2},
                });
            if (error) {
                console.error('Error updating user metadata:', error);
                return;
            } 
            setLoading(false);
            
        }
        catch(err){
            console.log("Failed to generate answer: ",err);
            toast.error("Failed to generate answer");
        }
        
    }

    const handlecopyToClipboard = () => {
        navigator.clipboard.writeText(questionAnswer);
        toast.success("Answer copied to clipboard!");
    }

    const newChat = () => {
        setQuestionAnswer("");
        setJobInfo({
            jobTitle: '',
            companyName: '',
            question: '',
            jobDescription: '',
            email: session?.user?.email 
        });
        setProfile(false);
    }

    const handleSignOut = async (e) => {
        e.preventDefault();
        await signOut();

    }

  return (
    apiForm ? <ApiKeyForm /> :( experienceData ? <ExperienceForm /> :
    <div className='dashboardcont'>
        <div className="sidebar">
            <GlassCard
                blurAmount={0}
                bgOpacity={0.6}
                contentBgOpacity={0.0}
                borderOpacity={0.125}
                noiseOpacity={0}
                borderRadius={18}
            >   
                <div className="sidebarcont">
                    <div className="topicons">
                        <img src={logoImg} alt="AnswerLy Logo" className="logo" onClick={() => setProfile(false)} />
                        <RiChatNewLine  className='newchat' onClick={newChat}/>
                    </div>
                    <div className="bottomicons">
                        <Tooltip 
                            title={
                                <div className='profileoptions'> {/* ✅ Need a wrapper div */}
                                    <p onClick={() => setProfile(true)}>Profile</p>
                                    <p onClick={handleSignOut} >Logout</p>
                                </div>
                            } 
                            placement='top' 
                            arrow 
                            interactive
                            slotProps={{
                                tooltip: {
                                    sx: {
                                        bgcolor: 'rgba(59, 59, 59, 0.05)', // ✅ Use bgcolor instead
                                        border: '0.5px solid rgba(255, 255, 255, 0.2);',
                                        borderRadius: '8px',
                                        padding: '12px',
                                        fontSize: '1rem',
                                        fontFamily: 'var(--font-mono)',
                                        backdropFilter: 'blur(10px)', // Optional: adds blur effect
                                    }
                                },
                                arrow: {
                                    sx: {
                                        color: 'rgba(59, 59, 59, 0.95)', // ✅ Match the tooltip background
                                        '&::before': {
                                            border: '0.5px solid rgba(255, 255, 255, 0.2);',
                                        }
                                    }
                                }
                            }}
                        >
                            <PiUserCircleThin className='profile'/>
                        </Tooltip>
                    </div>
                </div>
                
               
            </GlassCard>
        </div>
        <div className="maindashboard">
            <GlassCard
                blurAmount={0}
                bgOpacity={0.6}
                contentBgOpacity={0.0}
                borderOpacity={0.125}
                noiseOpacity={0}
                borderRadius={18}
            >
                {profile ? (
                    <ProfileForm />
                ) : questionAnswer ? (
                <div className="answercont">
                    <h1>{jobInfo.companyName}</h1>
                    <h1>{jobInfo.question}</h1>
                    <div className="answer">
                        <p>{questionAnswer}</p>
                        <IoCopyOutline className='copyIcon' onClick={handlecopyToClipboard} title="Copy to Clipboard"/>
                    </div>
                    <button className='jobformsubmit' onClick={() => setQuestionAnswer(false)}>Return to Dashboard</button>
                </div>
                ) : (
                <div className="maindashboardcont">
                     <div  className= 'requests' >
                        <div className='numrequests'>
                            <p >Requests/month</p>
                            <p >{session?.user?.user_metadata?.numberOfRequest} / 1000</p>
                        </div>
                        <div className='progressbar'>
                            <LinearProgress 
                            variant="determinate"
                            value={(session?.user?.user_metadata?.numberOfRequest/ 1000) * 100} 
                            sx={{ 
                                height: 8, 
                                borderRadius: 1,
                                backgroundColor: 'rgba(255, 255, 255, 0.1)', // Background track color
                                '& .MuiLinearProgress-bar': {
                                    backgroundColor: 'var(--accentColor)' // Progress bar color
                                }
                            }}
                            />
                        </div>
                        
                    </div> 
                    <h1>Hi there, <span>{session?.user?.user_metadata?.name}</span></h1>
                    <form className="jobinfoform" onSubmit={handleJobData}>
                    <h1>Please enter information about the job so we can</h1>
                    <h1>Get Started</h1>
                    <input
                        type="text"
                        placeholder="Job Title"
                        value={jobInfo.jobTitle}
                        onChange={(e) => setJobInfo({ ...jobInfo, jobTitle: e.target.value })}
                    />
                    <input
                        type="text"
                        placeholder="Company Name"
                        value={jobInfo.companyName}
                        onChange={(e) => setJobInfo({ ...jobInfo, companyName: e.target.value })}
                    />
                    <input
                        type="text"
                        placeholder="Question"
                        value={jobInfo.question}
                        onChange={(e) => setJobInfo({ ...jobInfo, question: e.target.value })}
                    />
                    <textarea
                        placeholder="Enter Job Description Here"
                        rows={8}
                        value={jobInfo.jobDescription}
                        onChange={(e) => setJobInfo({ ...jobInfo, jobDescription: e.target.value })}
                    />
                    <button type="submit" className="jobformsubmit" disabled={loading}>
                        {loading ? <CircularProgress size="25px" color='white' className='loader'/> : 'Generate Answer'}</button>
                    </form>
                </div>
                )}

                
            </GlassCard>
        </div>
        
    </div>)
  )
}

export default DashboardPage