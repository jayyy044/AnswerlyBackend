import "./HomePage.css"
import { useNavigate } from "react-router-dom";
import Button from "../../components/Button/Button";

const HomePage = () => {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate("/signup"); // 👈 change this to whatever route you want
  };
  return (
    <div className="homePageMainCont">
      <h1 >AnswerLy</h1>
      <p>An intelligent application companion</p>
      <button onClick={handleClick}>GET STARTED</button>

    </div>
  );
};



export default HomePage;