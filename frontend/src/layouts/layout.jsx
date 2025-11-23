import "./layout.css"
import { Outlet, useLocation } from 'react-router-dom';
import NavBar from '../Components/NavBar/NavBar'
import ParticleBackground from '../components/ParticleBackground/ParticleBackground'
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';


const Layout = () => {
  const location = useLocation();
  const hideNavRoutes = ['/signup', '/dashboard', '/signin']; // add more auth routes if needed
  const shouldHideNav = hideNavRoutes.includes(location.pathname);
  
  return (
    <ParticleBackground>
      {!shouldHideNav && <NavBar />}
      <Outlet />
      <ToastContainer
        position="top-right"
        autoClose={15000}
        hideProgressBar={true}
        newestOnTop={true}
        closeOnClick
        pauseOnHover
        theme="dark"
      />
    </ParticleBackground>
  );
}

export default Layout;
