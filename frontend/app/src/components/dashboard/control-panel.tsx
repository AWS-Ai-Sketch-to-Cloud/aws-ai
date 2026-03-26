"use client"

import { useState, useCallback } from "react"
import { Upload, Sparkles, FileText, Image as ImageIcon, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"

interface ControlPanelProps {
  onGenerate: (payload: { description: string; uploadedFile: File | null }) => void
  isGenerating: boolean
}

export function ControlPanel({ onGenerate, isGenerating }: ControlPanelProps) {
  const [description, setDescription] = useState("")
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith("image/")) {
      setUploadedFile(file)
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
    }
  }, [])

  const removeFile = useCallback(() => {
    setUploadedFile(null)
  }, [])

  return (
    <div className="flex flex-col gap-5">
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
            <FileText className="h-4 w-4 text-primary" strokeWidth={1.5} />
            아키텍처 요구사항
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="예) 서울 리전에 ALB + AutoScaling + RDS Multi-AZ 구성을 생성해 주세요."
            className="min-h-[140px] resize-none border-border/50 bg-input/50 text-sm placeholder:text-muted-foreground/60 focus-visible:ring-primary/50"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
            <ImageIcon className="h-4 w-4 text-primary" strokeWidth={1.5} />
            스케치 파일
          </CardTitle>
        </CardHeader>
        <CardContent>
          {uploadedFile ? (
            <div className="relative rounded-lg border border-border/50 bg-secondary/30 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  {uploadedFile.type.startsWith("image/") ? (
                    <ImageIcon className="h-5 w-5 text-primary" strokeWidth={1.5} />
                  ) : (
                    <FileText className="h-5 w-5 text-primary" strokeWidth={1.5} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">{uploadedFile.name}</p>
                  <p className="text-[11px] text-muted-foreground">{(uploadedFile.size / 1024).toFixed(1)} KB</p>
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={removeFile}>
                  <X className="h-4 w-4" strokeWidth={1.5} />
                </Button>
              </div>
            </div>
          ) : (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-all duration-200 ${
                isDragging ? "border-primary bg-primary/5" : "border-border/50 hover:border-border hover:bg-secondary/20"
              }`}
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary/50">
                <Upload className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
              </div>
              <p className="mt-3 text-sm font-medium text-foreground">이미지 업로드</p>
              <p className="mt-1 text-[11px] text-muted-foreground">PNG, JPG, WEBP</p>
              <input type="file" accept="image/*" onChange={handleFileSelect} className="absolute inset-0 cursor-pointer opacity-0" />
            </div>
          )}
        </CardContent>
      </Card>

      <Button
        size="lg"
        className="h-12 w-full bg-primary text-primary-foreground hover:bg-primary/90 transition-all duration-200"
        onClick={() => onGenerate({ description, uploadedFile })}
        disabled={isGenerating || (!description && !uploadedFile)}
      >
        {isGenerating ? (
          <>
            <Spinner className="mr-2 h-4 w-4" />
            분석 중...
          </>
        ) : (
          <>
            <Sparkles className="mr-2 h-4 w-4" strokeWidth={1.5} />
            AI 아키텍처 생성
          </>
        )}
      </Button>
    </div>
  )
}
