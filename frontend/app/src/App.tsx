<<<<<<< HEAD
import { useState } from "react";
import { Header } from "@/components/dashboard/header";
import { ControlPanel } from "@/components/dashboard/control-panel";
import { ResultPanel } from "@/components/dashboard/result-panel";
=======
import { BrowserRouter as Router, Routes, Route } from "react-router";
import NotFound from "./pages/OtherPage/NotFound";
import AppLayout from "./layout/AppLayout";
import { ScrollToTop } from "./components/common/ScrollToTop";
import SketchConsole from "./pages/Console/SketchConsole";
import LoginPage from "./pages/Auth/LoginPage";
>>>>>>> 126ab9bd0496d9b110b600c11f4997c7cef48919

export default function App() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<"idle" | "analyzing" | "complete" | "optimized">("idle");
  const [activeTab, setActiveTab] = useState<"architecture" | "terraform" | "cost">("architecture");

  const handleGenerate = () => {
    setIsGenerating(true);
    setGenerationStatus("analyzing");

    setTimeout(() => {
      setGenerationStatus("complete");
      setTimeout(() => {
        setGenerationStatus("optimized");
        setIsGenerating(false);
      }, 1000);
    }, 2000);
  };

  return (
<<<<<<< HEAD
    <div className="min-h-screen bg-background">
      <Header generationStatus={generationStatus} />

      <main className="container mx-auto px-4 py-6 lg:px-6">
        <div className="grid gap-6 lg:grid-cols-[420px_1fr] xl:grid-cols-[480px_1fr]">
          <ControlPanel onGenerate={handleGenerate} isGenerating={isGenerating} />
          <ResultPanel
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            generationStatus={generationStatus}
          />
        </div>
      </main>
    </div>
=======
    <>
      <Router>
        <ScrollToTop />
        <Routes>
          <Route index path="/" element={<LoginPage />} />
          <Route element={<AppLayout />}>
            <Route path="/console" element={<SketchConsole />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Router>
    </>
>>>>>>> 126ab9bd0496d9b110b600c11f4997c7cef48919
  );
}
