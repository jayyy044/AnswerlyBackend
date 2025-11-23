import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from './supabaseClient';

const AuthContext = createContext();


export const AuthProvider = ({ children }) => {
//   const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [session, setSession] = useState(undefined);
    useEffect(() => {
        supabase.auth.getSession().then(({ data: { session } }) => {
            setSession(session);
            setLoading(false);
        });
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setSession(session);
            setLoading(false);
        });
        
        return () => subscription.unsubscribe();
    }, [])

    const signUpNewUser = async (email, password, name) => {
        const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: {
                data: { 
                    name,
                    geminiKey: false,
                    tavilyKey: false,
                    experienceData: false,
                    numberOfRequest: 0
                 },
                emailRedirectTo: `${window.location.origin}/signin`
            },
        });
        
        if (error) {
            console.error("There was an error signing up:", error);
            return { success: false, error };
        }

    // With email confirmation enabled, there's no session until email is confirmed
        return { 
            success: true, 
            data,
            requiresEmailConfirmation: true 
        };
    };
    
    
    const signOut = async() => {
        const {error} = supabase.auth.signOut();
        if(error){
            console.error("There was a problem:", error)
        }
    }

    const signInUser = async (email, password) => {
        try {
            const { data, error } = await supabase.auth.signInWithPassword({
                email: email,
                password: password,
            });
            
            if (error) {
                console.error("There was an error signing in:", error);
                return { success: false, error};
            }
            
            return { success: true, data };
        } catch (error) {
            console.error("There was an error signing in:", error);
            return { success: false, error: error.message }; 
    }
}


  return (
    <AuthContext.Provider value={{session, signUpNewUser, signOut, signInUser, loading}}>
      {children}
    </AuthContext.Provider>
  );
  
};

export const useAuth = () => {
  return useContext(AuthContext);
};