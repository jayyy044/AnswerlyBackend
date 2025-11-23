// import './ApiKeyForm.css'
import GlassCard from '../GlassCard/GlassCard'
import './ApiKeyForm.css'
import { supabase } from '../context/supabaseClient'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { toast } from 'react-toastify'
import CircularProgress from '@mui/material/CircularProgress'


const ApiKeyFrom = () => {
  const [formData, setFormData] = useState({
    geminiKey: "",
    tavilyKey: ""
  })
  const { session } = useAuth();
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault();

    setLoading(true);
    
    try{
      const response = await fetch('/api/user/apikeys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`
        },
        body: JSON.stringify({ geminiKey: formData.geminiKey, tavilyKey: formData.tavilyKey, email: session.user.user_metadata.email })
      });
      const respData = await response.json();
      if(!response.ok){
        console.error("An error occured while trying to save api keys: ", respData.error);
        toast.error("Failed to save api keys");
        return;
      }

      console.log("Success: ",respData.message)
      const { data, error } = await supabase.auth.updateUser({
      data: { geminiKey: true, tavilyKey: true, numberOfRequest: 1},
      });
      if (error) {
        console.error('Error updating user metadata:', error);
        toast.error("Failed to save api keys");
        return;
      } 
      console.log('User metadata updated successfully:', data);
      setLoading(false);
      
      window.location.reload();
    }
    catch(err){
      console.log("Failed to save api keys: ",err);
      toast.error("Failed to save api keys");
    }

  };

  return (
    <div className='keyFormCont'>
        <GlassCard
            blurAmount={0}
            bgOpacity={0.8}
            contentBgOpacity={0.0}
            borderOpacity={0.125}
            noiseOpacity={0.0}
            borderRadius={18}
        
        >
            <form className="keyform" onSubmit={handleSubmit}>
              <h1>Please Enter Your</h1>
              <h1>API Keys</h1>
              <a href='https://google.com'  target="_blank" rel="noopener noreferrer">Tutorial for getting keys</a>
                <input type='password' value={formData.geminiKey} onChange={(e) => setFormData({...formData, geminiKey: e.target.value})} placeholder='Gemini Key'/>
                <input  type='password' value={formData.tavilyKey} onChange={(e) => setFormData({...formData, tavilyKey: e.target.value})} placeholder='Tavily Key'/>
              <button type='submit' className='keyformbtn' disabled={loading}>
                {loading ? <CircularProgress size="25px" color="white" className='loader'/> : 'Submit'}
                </button> 
            </form>
        </GlassCard>

    </div>
  )
}

export default ApiKeyFrom