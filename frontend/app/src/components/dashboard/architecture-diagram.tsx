"use client"

import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  Handle,
  Position,
  MarkerType,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { Cloud, Database, Server, Globe, Shield, HardDrive } from "lucide-react"
import { Empty, EmptyMedia, EmptyTitle, EmptyDescription } from "@/components/ui/empty"

interface ArchitectureDiagramProps {
  generationStatus: "idle" | "analyzing" | "complete" | "optimized"
}

// Custom Node Component
function CustomNode({ data }: { data: { label: string; icon: string; type: string } }) {
  const iconMap: Record<string, React.ReactNode> = {
    cloud: <Cloud className="h-5 w-5" strokeWidth={1.5} />,
    database: <Database className="h-5 w-5" strokeWidth={1.5} />,
    server: <Server className="h-5 w-5" strokeWidth={1.5} />,
    globe: <Globe className="h-5 w-5" strokeWidth={1.5} />,
    shield: <Shield className="h-5 w-5" strokeWidth={1.5} />,
    storage: <HardDrive className="h-5 w-5" strokeWidth={1.5} />,
  }

  const typeColors: Record<string, string> = {
    entry: "bg-primary/20 text-primary border-primary/30",
    compute: "bg-chart-2/20 text-chart-2 border-chart-2/30",
    database: "bg-chart-4/20 text-chart-4 border-chart-4/30",
    storage: "bg-chart-3/20 text-chart-3 border-chart-3/30",
    network: "bg-chart-1/20 text-chart-1 border-chart-1/30",
  }

  return (
    <div className={`rounded-xl border px-4 py-3 backdrop-blur-sm ${typeColors[data.type] || typeColors.compute}`}>
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground/50 !w-2 !h-2 !border-0" />
      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-background/50">
          {iconMap[data.icon] || iconMap.server}
        </div>
        <span className="text-xs font-medium whitespace-nowrap">{data.label}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-muted-foreground/50 !w-2 !h-2 !border-0" />
    </div>
  )
}

const nodeTypes = {
  custom: CustomNode,
}

const initialNodes: Node[] = [
  {
    id: "1",
    type: "custom",
    position: { x: 250, y: 0 },
    data: { label: "Route 53", icon: "globe", type: "entry" },
  },
  {
    id: "2",
    type: "custom",
    position: { x: 250, y: 100 },
    data: { label: "CloudFront CDN", icon: "cloud", type: "network" },
  },
  {
    id: "3",
    type: "custom",
    position: { x: 250, y: 200 },
    data: { label: "ALB (Application Load Balancer)", icon: "shield", type: "network" },
  },
  {
    id: "4",
    type: "custom",
    position: { x: 100, y: 320 },
    data: { label: "EC2 Auto Scaling (AZ-1)", icon: "server", type: "compute" },
  },
  {
    id: "5",
    type: "custom",
    position: { x: 400, y: 320 },
    data: { label: "EC2 Auto Scaling (AZ-2)", icon: "server", type: "compute" },
  },
  {
    id: "6",
    type: "custom",
    position: { x: 100, y: 450 },
    data: { label: "RDS Primary (AZ-1)", icon: "database", type: "database" },
  },
  {
    id: "7",
    type: "custom",
    position: { x: 400, y: 450 },
    data: { label: "RDS Standby (AZ-2)", icon: "database", type: "database" },
  },
  {
    id: "8",
    type: "custom",
    position: { x: 250, y: 560 },
    data: { label: "S3 Bucket", icon: "storage", type: "storage" },
  },
]

const initialEdges: Edge[] = [
  { id: "e1-2", source: "1", target: "2", animated: true, style: { stroke: "var(--primary)", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "var(--primary)" } },
  { id: "e2-3", source: "2", target: "3", animated: true, style: { stroke: "var(--primary)", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "var(--primary)" } },
  { id: "e3-4", source: "3", target: "4", style: { stroke: "var(--chart-2)", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "var(--chart-2)" } },
  { id: "e3-5", source: "3", target: "5", style: { stroke: "var(--chart-2)", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "var(--chart-2)" } },
  { id: "e4-6", source: "4", target: "6", style: { stroke: "var(--chart-4)", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "var(--chart-4)" } },
  { id: "e5-7", source: "5", target: "7", style: { stroke: "var(--chart-4)", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "var(--chart-4)" } },
  { id: "e6-7", source: "6", target: "7", style: { stroke: "var(--chart-4)", strokeWidth: 1.5, strokeDasharray: "5,5" }, label: "복제", labelStyle: { fill: "var(--muted-foreground)", fontSize: 10 } },
  { id: "e6-8", source: "6", target: "8", style: { stroke: "var(--chart-3)", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "var(--chart-3)" } },
  { id: "e7-8", source: "7", target: "8", style: { stroke: "var(--chart-3)", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "var(--chart-3)" } },
]

export function ArchitectureDiagram({ generationStatus }: ArchitectureDiagramProps) {
  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  if (generationStatus === "idle") {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <Empty className="border-0">
          <EmptyMedia variant="icon">
            <Cloud className="h-6 w-6" strokeWidth={1.5} />
          </EmptyMedia>
          <EmptyTitle>아키텍처 다이어그램</EmptyTitle>
          <EmptyDescription>
            인프라 요구사항을 입력하고 생성 버튼을 클릭하면
            <br />
            AI가 최적의 클라우드 아키텍처를 설계합니다
          </EmptyDescription>
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
            <Cloud className="absolute left-1/2 top-1/2 h-6 w-6 -translate-x-1/2 -translate-y-1/2 text-primary" strokeWidth={1.5} />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">아키텍처 분석 중...</p>
            <p className="text-xs text-muted-foreground">AI가 최적의 설계를 생성하고 있습니다</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-[600px] w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        className="bg-background"
      >
        <Background color="var(--border)" gap={20} size={1} />
        <Controls 
          className="!bg-card !border-border/50 !rounded-lg !shadow-none [&>button]:!bg-card [&>button]:!border-border/50 [&>button]:!text-muted-foreground [&>button:hover]:!bg-secondary [&>button:hover]:!text-foreground"
          showInteractive={false}
        />
      </ReactFlow>
    </div>
  )
}
