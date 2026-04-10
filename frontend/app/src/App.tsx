import { BrowserRouter as Router, Navigate, Route, Routes } from "react-router";
import { ScrollToTop } from "./components/common/ScrollToTop";
import { Toaster } from "./components/ui/toaster";
import AppLayout from "./layout/AppLayout";
import HomePage from "./pages/Home/HomePage";
import LoginPage from "./pages/Auth/LoginPage";
import SocialCallbackPage from "./pages/Auth/SocialCallbackPage";
import SignupPage from "./pages/Auth/SignupPage";
import SketchConsole from "./pages/Console/SketchConsole";
import NotFound from "./pages/OtherPage/NotFound";

export default function App() {
  return (
    <Router>
      <ScrollToTop />
      <Toaster />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/auth/social/callback" element={<SocialCallbackPage />} />
        <Route path="/dashboard" element={<Navigate to="/workspace" replace />} />
        <Route element={<AppLayout />}>
          <Route path="/workspace" element={<SketchConsole page="workspace" />} />
          <Route path="/projects" element={<SketchConsole page="projects" />} />
          <Route path="/deploy" element={<SketchConsole page="deploy" />} />
          <Route path="/settings" element={<SketchConsole page="settings" />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}
