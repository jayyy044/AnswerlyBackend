import './SigninPage.css'
import GlassCard from "../../components/GlassCard/GlassCard"
import { useAuth } from '../../components/context/AuthContext'
import { useNavigate } from "react-router-dom"
import { useState } from 'react'
import CircularProgress from '@mui/material/CircularProgress';


const SigninPage = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const {signInUser } = useAuth();

    const handleSignIn = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        try{
            const result = await signInUser(email, password);
            if(result.success){
                navigate('/dashboard');
            }
            else{
                setError(result.error?.message || 'Signup failed');
                console.error("There was a problem signing in:", result.error?.message || 'Sign-up failed');
            }
        }
        catch(err){
            setError(err.message);
            console.error("There was a problem signing in:", err.message);
        }
        finally{
            setLoading(false);
        }
    }



  return (
    <div className='signinPageCont'>
        <GlassCard 
            blurAmount={0}          // blur of the glass
            bgOpacity={0.85}          // background opacity
            contentBgOpacity={0.0}   // content background opacity
            borderOpacity={0.125}     // border transparency
            noiseOpacity={0.0}      // subtle noise
            borderRadius={18}        // border radius
        >

            <form className="signinForm" onSubmit={handleSignIn}>
                <h1>Welcome</h1>
                <h1>Back</h1>
                <p>Don't have an account <a onClick={() => navigate('/signup')}>Sign Up</a></p>
                <div className="formInputsSI">
                    <input onChange={(e) => setEmail(e.target.value)} type="email" placeholder="Email" />
                    <input onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" />
                </div>  
                {error && <p className='errormsg'>{error}</p>}
                <button className= "signinbtn" type="submit" disabled={loading}>
                    {loading ? <CircularProgress size="25px" color="white" className="loader"/> : "Sign In"}
                </button>
            </form>
        </GlassCard>
    </div>
  )
}

export default SigninPage