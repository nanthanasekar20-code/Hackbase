import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/layout/Layout.jsx";
import RequireAuth from "./components/auth/RequireAuth.jsx";
import Home from "./pages/Home.jsx";
import Discover from "./pages/Discover.jsx";
import ProblemDetails from "./pages/ProblemDetails.jsx";
import Roadmap from "./pages/Roadmap.jsx";
import Roadmaps from "./pages/Roadmaps.jsx";
import Resources from "./pages/Resources.jsx";
import MyProjects from "./pages/MyProjects.jsx";
import HowItWorks from "./pages/HowItWorks.jsx";
import Tracking from "./pages/Tracking.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Profile from "./pages/Profile.jsx";
import NotFound from "./pages/NotFound.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/discover" element={<Discover />} />
          {/* Legacy route from the original scaffold — keep old links working */}
          <Route path="/results" element={<Navigate to="/discover" replace />} />
          <Route path="/problem/:id" element={<ProblemDetails />} />
          <Route path="/roadmap" element={<Navigate to="/roadmaps" replace />} />
          <Route
            path="/roadmap/:id"
            element={
              <RequireAuth>
                <Roadmap />
              </RequireAuth>
            }
          />
          <Route
            path="/roadmaps"
            element={
              <RequireAuth>
                <Roadmaps />
              </RequireAuth>
            }
          />
          <Route path="/resources" element={<Resources />} />
          <Route
            path="/projects"
            element={
              <RequireAuth>
                <MyProjects />
              </RequireAuth>
            }
          />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route
            path="/tracking"
            element={
              <RequireAuth requireAdmin>
                <Tracking />
              </RequireAuth>
            }
          />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/profile"
            element={
              <RequireAuth>
                <Profile />
              </RequireAuth>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
