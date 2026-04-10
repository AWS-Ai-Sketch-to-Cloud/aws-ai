"use client";

import { useCallback, useState } from "react";
import {
  FileText,
  Image as ImageIcon,
  Sparkles,
  Upload,
  WandSparkles,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

interface ControlPanelProps {
  onGenerate: (payload: { description: string; uploadedFile: File | null }) => void;
  isGenerating: boolean;
}

const QUICK_HINTS = [
  "서울 리전, ALB, Auto Scaling, RDS Multi-AZ",
  "React 프론트와 FastAPI 백엔드, S3 정적 호스팅, CloudFront",
  "Bedrock 호출 포함, 비공개 서브넷, 모니터링과 로그 수집",
];

export function ControlPanel({ onGenerate, isGenerating }: ControlPanelProps) {
  const [description, setDescription] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      setUploadedFile(file);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFile(file);
    }
  }, []);

  return (
    <div className="flex flex-col gap-5">
      <Card>
        <div className="h-1 w-full bg-[linear-gradient(90deg,#487bff_0%,#58e1c1_100%)]" />
        <CardHeader className="space-y-3 pb-3">
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-[#d9e4f2] bg-[#f8fbff] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#487bff]">
            <WandSparkles className="h-3.5 w-3.5" />
            Input
          </div>
          <CardTitle className="flex items-center gap-2 text-xl">
            <FileText className="h-5 w-5 text-[#487bff]" />
            아키텍처 요구사항
          </CardTitle>
          <p className="text-sm leading-6 text-[#65748b]">
            서비스 목적, 예상 트래픽, 보안 요구사항, 데이터 저장 방식을 적을수록 더
            구체적인 AWS 구조를 얻을 수 있습니다.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="예) 서울 리전 기준으로 React 프론트엔드와 FastAPI 백엔드를 운영하고, ALB 뒤에 EC2 Auto Scaling을 두고 RDS Multi-AZ와 S3 업로드 버킷, Bedrock 호출 로그 저장, CloudWatch 모니터링까지 포함해 주세요."
            className="min-h-[220px]"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />

          <div className="flex flex-wrap gap-2">
            {QUICK_HINTS.map((hint) => (
              <button
                key={hint}
                type="button"
                onClick={() =>
                  setDescription((current) => (current.trim() ? `${current}\n- ${hint}` : hint))
                }
                className="rounded-full border border-[#d9e4f2] bg-white px-3 py-1.5 text-xs font-medium text-[#52627a] transition hover:border-[#487bff] hover:text-[#487bff]"
              >
                {hint}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <ImageIcon className="h-5 w-5 text-[#487bff]" />
            스케치 파일
          </CardTitle>
          <p className="text-sm text-[#65748b]">
            손그림, 다이어그램, 화이트보드 캡처를 올리면 텍스트 설명과 함께
            해석합니다.
          </p>
        </CardHeader>
        <CardContent>
          {uploadedFile ? (
            <div className="relative rounded-[1.25rem] border border-[#d9e4f2] bg-[#f8fbff] p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#edf3ff]">
                  {uploadedFile.type.startsWith("image/") ? (
                    <ImageIcon className="h-5 w-5 text-[#487bff]" />
                  ) : (
                    <FileText className="h-5 w-5 text-[#487bff]" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-[#122033]">{uploadedFile.name}</p>
                  <p className="text-xs text-[#65748b]">
                    {(uploadedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9 rounded-xl"
                  onClick={() => setUploadedFile(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`relative flex flex-col items-center justify-center rounded-[1.5rem] border-2 border-dashed p-8 text-center transition-all duration-200 ${
                isDragging
                  ? "border-[#487bff] bg-[#edf4ff]"
                  : "border-[#d9e4f2] bg-[#f9fbff] hover:border-[#487bff] hover:bg-[#f3f8ff]"
              }`}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white shadow-sm">
                <Upload className="h-5 w-5 text-[#487bff]" />
              </div>
              <p className="mt-4 text-sm font-semibold text-[#122033]">
                이미지를 드래그하거나 클릭해서 업로드
              </p>
              <p className="mt-1 text-xs text-[#65748b]">PNG, JPG, WEBP 지원</p>
              <input
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="absolute inset-0 cursor-pointer opacity-0"
              />
            </div>
          )}
        </CardContent>
      </Card>

      <Button
        size="lg"
        className="h-13 w-full"
        onClick={() => onGenerate({ description, uploadedFile })}
        disabled={isGenerating || (!description && !uploadedFile)}
      >
        {isGenerating ? (
          <>
            <Spinner className="mr-2 h-4 w-4" />
            AI가 요구사항을 해석하는 중...
          </>
        ) : (
          <>
            <Sparkles className="mr-2 h-4 w-4" />
            AI 아키텍처 생성 시작
          </>
        )}
      </Button>
    </div>
  );
}
