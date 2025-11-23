import { useAuth } from "./AuthContext"
import { Navigate } from "react-router-dom"

const PrivateRoutes = ({ children }) => {
    const { session, loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>;
    }


  return (<>{session ? <>{children}</> : <Navigate to="/signin" />}</>)
}

export default PrivateRoutes