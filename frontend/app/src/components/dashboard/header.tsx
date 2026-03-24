"use client"

import { Cloud, Settings, Bell, User } from "lucide-react"
import { useNavigate } from "react-router"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"

interface HeaderProps {
  generationStatus: "idle" | "analyzing" | "complete" | "optimized"
}

const statusConfig = {
  idle: { label: "대기 중", variant: "secondary" as const },
  analyzing: { label: "분석 중...", variant: "default" as const },
  complete: { label: "설계 완료", variant: "default" as const },
  optimized: { label: "비용 최적화 됨", variant: "default" as const },
}

export function Header({ generationStatus }: HeaderProps) {
  const navigate = useNavigate()
  const status = statusConfig[generationStatus]

  const handleLogout = () => {
    sessionStorage.removeItem("stc-auth")
    navigate("/")
  }

  return (
    <header className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-xl">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 lg:px-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <Cloud className="h-5 w-5 text-primary" strokeWidth={1.5} />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-tight text-foreground">
                Sketch-to-Cloud
              </span>
              <span className="text-[10px] text-muted-foreground">
                지능형 인프라 설계 비서
              </span>
            </div>
          </div>
          
          {generationStatus !== "idle" && (
            <Badge 
              variant={status.variant}
              className={`ml-4 ${generationStatus === "analyzing" ? "animate-pulse" : ""} ${
                generationStatus === "optimized" 
                  ? "bg-success/10 text-success border-success/20" 
                  : ""
              }`}
            >
              {status.label}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-9 w-9 text-muted-foreground hover:text-foreground">
            <Bell className="h-4 w-4" strokeWidth={1.5} />
            <span className="sr-only">알림</span>
          </Button>
          
          <Button variant="ghost" size="icon" className="h-9 w-9 text-muted-foreground hover:text-foreground">
            <Settings className="h-4 w-4" strokeWidth={1.5} />
            <span className="sr-only">설정</span>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-9 w-9 text-muted-foreground hover:text-foreground">
                <User className="h-4 w-4" strokeWidth={1.5} />
                <span className="sr-only">사용자 메뉴</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem>프로필</DropdownMenuItem>
              <DropdownMenuItem>팀 설정</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout}>로그아웃</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
