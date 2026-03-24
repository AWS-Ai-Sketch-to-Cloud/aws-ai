"use client"

import { useState } from "react"
import { Copy, Check, Download, FileCode } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { ScrollArea } from "@/components/ui/scroll-area"

interface TerraformCodeProps {
  generationStatus: "idle" | "analyzing" | "complete" | "optimized"
  terraformCode?: string | null
}

const fallbackTerraformCode = `terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}`

export function TerraformCode({ generationStatus, terraformCode }: TerraformCodeProps) {
  const [copied, setCopied] = useState(false)
  const code = terraformCode?.trim() ? terraformCode : fallbackTerraformCode

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadCode = () => {
    const blob = new Blob([code], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "main.tf"
    a.click()
    URL.revokeObjectURL(url)
  }

  if (generationStatus === "idle") {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <Empty>
          <EmptyMedia variant="icon"><FileCode className="h-10 w-10" strokeWidth={1} /></EmptyMedia>
          <EmptyTitle>Terraform 코드</EmptyTitle>
          <EmptyDescription>분석이 완료되면 Terraform 코드가 표시됩니다.</EmptyDescription>
        </Empty>
      </div>
    )
  }

  if (generationStatus === "analyzing") {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="h-16 w-16 animate-spin rounded-full border-2 border-muted border-t-primary" />
            <FileCode className="absolute left-1/2 top-1/2 h-6 w-6 -translate-x-1/2 -translate-y-1/2 text-primary" strokeWidth={1.5} />
          </div>
          <div className="text-center"><p className="text-sm font-medium text-foreground">코드 생성 중...</p></div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-[600px] flex-col">
      <div className="flex items-center justify-between border-b border-border/30 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">main.tf</span>
          <span className="rounded bg-secondary/50 px-1.5 py-0.5 text-[10px] text-muted-foreground">HCL</span>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground" onClick={copyToClipboard}>
            {copied ? <Check className="mr-1.5 h-3.5 w-3.5 text-success" strokeWidth={1.5} /> : <Copy className="mr-1.5 h-3.5 w-3.5" strokeWidth={1.5} />}
            {copied ? "복사됨" : "복사"}
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground" onClick={downloadCode}>
            <Download className="mr-1.5 h-3.5 w-3.5" strokeWidth={1.5} />다운로드
          </Button>
        </div>
      </div>
      <ScrollArea className="flex-1">
        <pre className="p-4 text-xs leading-relaxed"><code className="font-mono text-foreground/90">{code}</code></pre>
      </ScrollArea>
    </div>
  )
}
