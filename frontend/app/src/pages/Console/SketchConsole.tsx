import { useState } from "react";
import PageMeta from "../../components/common/PageMeta";
import { Header } from "../../components/dashboard/header";
import { ControlPanel } from "../../components/dashboard/control-panel";
import { ResultPanel } from "../../components/dashboard/result-panel";

export default function SketchConsole() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<
    "idle" | "analyzing" | "complete" | "optimized"
  >("idle");
  const [activeTab, setActiveTab] = useState<
    "architecture" | "terraform" | "cost"
  >("architecture");

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
    <>
      <PageMeta
        title="Console | Sketch-to-Cloud"
        description="Sketch-to-Cloud 메인 대시보드"
      />
      <div className="min-h-screen bg-background">
        <Header generationStatus={generationStatus} />

        <main className="container mx-auto px-4 py-6 lg:px-6">
          <div className="grid gap-6 lg:grid-cols-[420px_1fr] xl:grid-cols-[480px_1fr]">
            <ControlPanel
              onGenerate={handleGenerate}
              isGenerating={isGenerating}
            />
            <ResultPanel
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              generationStatus={generationStatus}
            />
          </div>
        </main>
      </div>
    </>
  );
}
