import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/layout/Layout.jsx";
import RequireAuth from "./components/auth/RequireAuth.jsx";
import Home from "./pages/Home.jsx";
import Discover from "./pages/Discover.jsx";
import Domains from "./pages/Domains.jsx";
import AllProblems from "./pages/AllProblems.jsx";
import LiveHackathons from "./pages/LiveHackathons.jsx";
import ProblemDetails from "./pages/ProblemDetails.jsx";
import Roadmap from "./pages/Roadmap.jsx";
import MyProjects from "./pages/MyProjects.jsx";
import HowItWorks from "./pages/HowItWorks.jsx";
import Tracking from "./pages/Tracking.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import Profile from "./pages/Profile.jsx";
import NotFound from "./pages/NotFound.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/discover" element={<Discover />} />
          <Route path="/domains" element={<Domains />} />
          {/* Legacy route from the original scaffold — keep old links working */}
          <Route path="/results" element={<Navigate to="/discover" replace />} />
          <Route path="/problems" element={<AllProblems />} />
          <Route path="/problem/:id" element={<ProblemDetails />} />
          <Route path="/live-hackathons" element={<LiveHackathons />} />
          {/* Legacy route — "Roadmaps" (the listing page) was removed as a
              near-duplicate of "My Projects" (same data, same cards, plus
              filtering); this used to redirect there, now goes straight to
              My Projects. */}
          <Route path="/roadmap" element={<Navigate to="/projects" replace />} />
          <Route path="/roadmaps" element={<Navigate to="/projects" replace />} />
          <Route
            path="/roadmap/:id"
            element={
              <RequireAuth>
                <Roadmap />
              </RequireAuth>
            }
          />
          {/* Legacy route — Resources was removed (it duplicated nothing
              useful; roadmap starter resources already live on the
              Roadmap page's own sidebar). */}
          <Route path="/resources" element={<Navigate to="/projects" replace />} />
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
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
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
