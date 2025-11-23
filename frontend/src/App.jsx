import './App.css';
import {
  Route,
  createBrowserRouter,
  createRoutesFromElements,
  RouterProvider
} from 'react-router-dom';
import Layout from './layouts/layout';
import HomePage from './pages/Homepage/HomePage';
import SignupPage from './pages/Signuppage/SignupPage';
import DashboardPage from './pages/DashboardPage/DashboardPage';
import SigninPage from './pages/SigninPage/SigninPage';
import PrivateRoutes from './components/context/PrivateRoutes';

function App() {
  const router = createBrowserRouter(
    createRoutesFromElements(
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path ="/signin" element={<SigninPage />} />
        <Route path="/dashboard" element={<PrivateRoutes><DashboardPage/></PrivateRoutes>} />
      </Route>
    )
  );

  return <RouterProvider router={router} />;
}

export default App;
