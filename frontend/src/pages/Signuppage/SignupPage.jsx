import "./SignupPage.css"
import GlassCard from '../../components/GlassCard/GlassCard'
import { useNavigate } from "react-router-dom"
import { useState } from "react"
import { useAuth } from "../../components/context/AuthContext"
import CircularProgress from '@mui/material/CircularProgress';

const SignupPage = () => {
    const navigate = useNavigate();
    const { session, signUpNewUser } = useAuth();
    
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState({
        text: "",
        type: "", // "success" or "error"
    });
    const [formData, setFormData] = useState({
        name: "",
        email: "",
        password: ""
    });

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
        
        // Clear message when user starts typing
        if (message.text) {
            setMessage({ text: "", type: "" });
        }
    };

    const handlesignUp = async (e) => {
        e.preventDefault();
        setLoading(true);
        setMessage({ text: "", type: "" }); // Clear previous messages
        
        console.log("User Data Received!", formData);
        
        try {
            const result = await signUpNewUser(
                formData.email.trim(),
                formData.password,
                formData.name.trim()    
            );
            
            if (result.success) {
                if (result.requiresEmailConfirmation) {
                    setMessage({
                        text: "Success! Please check your email to confirm your account.",
                        type: "success"
                    });
                    console.log("Success! Please check your email to confirm your account.");
                    setFormData({ name: "", email: "", password: "" });
                }
            } else {
                const errorMessage = result.error?.message || 'Signup failed';
    
                let displayMessage = errorMessage;
                
                if (errorMessage.includes("Password should contain at least one character")) {
                    displayMessage = "Password must contain at least one lowercase letter, one uppercase letter, one number, and one special character";
                } else if (errorMessage.includes("Email address")) {
                    displayMessage = "Please enter a valid email address";
                } else if (errorMessage.includes("should be at least") || errorMessage.includes("least 6 characters")) {
                    displayMessage = "Password must be at least 6 characters long";
                }

                setMessage({
                    text: displayMessage,
                    type: "error"
                });
                console.error("There was an error signing up1212:", message.text);
            }
        } catch (err) {
            setMessage({
                text: err.message || 'An unexpected error occurred',
                type: "error"
            });
            console.error("There was an error signing up:", message.text);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className='signupPageCont'>
            <GlassCard 
                blurAmount={0}
                bgOpacity={0.85}
                contentBgOpacity={0.0}
                borderOpacity={0.125}
                noiseOpacity={0.0}
                borderRadius={18}
            >
                <form className="signupForm" onSubmit={handlesignUp}>
                    <h1>Create an</h1>
                    <h1>Account</h1>
                    <p>Already have an account <a onClick={() => navigate('/signin')}>Sign in</a></p>
                    
                    <div className="formInputsSU">
                        <input 
                            name="name"
                            type="text" 
                            placeholder="Name"
                            value={formData.name}
                            onChange={handleChange}
                            disabled={loading}
                        />
                        <input 
                            name="email"
                            type="email" 
                            placeholder="Email"
                            value={formData.email}
                            onChange={handleChange}
                            disabled={loading}
                        />
                        <input 
                            name="password"
                            type="password" 
                            placeholder="Password"
                            value={formData.password}
                            onChange={handleChange}
                            disabled={loading}
                        />
                    </div>
                    
                    {message.text && (
                        <p className={`message ${message.type}`}>
                            {message.text}
                        </p>
                    )}
                    
                    <button 
                        className="signupbtn" 
                        type="submit" 
                        disabled={loading}
                    >
                        {loading ? <CircularProgress size="25px" color="white" className="loader"/> : "Sign Up"}
                        
                    </button>
                </form>
            </GlassCard>
        </div>
    )
}

export default SignupPage