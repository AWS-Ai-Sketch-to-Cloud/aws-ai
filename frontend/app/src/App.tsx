import { BrowserRouter as Router, Route, Routes } from "react-router";
import { ScrollToTop } from "./components/common/ScrollToTop";
import { Toaster } from "./components/ui/toaster";
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
        <Route path="/" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/auth/social/callback" element={<SocialCallbackPage />} />
        <Route path="/dashboard" element={<SketchConsole />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}
