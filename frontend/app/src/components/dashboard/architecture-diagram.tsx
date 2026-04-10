"use client";

import { useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Bot, Cloud, Database, Globe, Server } from "lucide-react";
import { Empty, EmptyDescription, EmptyMedia, EmptyTitle } from "@/components/ui/empty";

interface ArchitectureDiagramProps {
  generationStatus: "idle" | "analyzing" | "complete" | "optimized";
  architectureJson?: {
    ec2?: { count?: number; instance_type?: string };
    rds?: { enabled?: boolean; engine?: string | null };
    bedrock?: { enabled?: boolean; model?: string | null };
    additional_services?: string[];
    public?: boolean;
    region?: string;
  } | null;
  rationale?: {
    summary?: string;
    intentPoints?: string[];
    designPoints?: string[];
    whyBetter?: string[];
  } | null;
}

function CustomNode({
  data,
}: {
  data: { label: string; icon: "globe" | "cloud" | "server" | "database" | "bot" };
}) {
  const iconMap = {
    globe: <Globe className="h-5 w-5" strokeWidth={1.8} />,
    cloud: <Cloud className="h-5 w-5" strokeWidth={1.8} />,
    server: <Server className="h-5 w-5" strokeWidth={1.8} />,
    database: <Database className="h-5 w-5" strokeWidth={1.8} />,
    bot: <Bot className="h-5 w-5" strokeWidth={1.8} />,
  };

  return (
    <div className="rounded-2xl border border-[#d9e4f2] bg-white/92 px-4 py-3 shadow-[0_18px_40px_rgba(72,123,255,0.12)] backdrop-blur-sm">
      <Handle type="target" position={Position.Top} className="!h-2.5 !w-2.5 !border-0 !bg-[#487bff]/70" />
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#edf3ff] text-[#487bff]">
          {iconMap[data.icon]}
        </div>
        <span className="whitespace-nowrap text-xs font-semibold text-[#122033]">{data.label}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-2.5 !w-2.5 !border-0 !bg-[#58e1c1]/80" />
    </div>
  );
}

const nodeTypes = { custom: CustomNode };

function buildGraph(
  architectureJson: ArchitectureDiagramProps["architectureJson"],
): { nodes: Node[]; edges: Edge[] } {
  const region = architectureJson?.region ?? "ap-northeast-2";
  const ec2Count = architectureJson?.ec2?.count ?? 1;
  const ec2Type = architectureJson?.ec2?.instance_type ?? "t3.micro";
  const rdsEnabled = Boolean(architectureJson?.rds?.enabled);
  const rdsEngine = architectureJson?.rds?.engine ?? "mysql";
  const bedrockEnabled = Boolean(architectureJson?.bedrock?.enabled);
  const bedrockModel =
    architectureJson?.bedrock?.model ?? "anthropic.claude-3-haiku-20240307-v1:0";
  const additionalServices = (architectureJson?.additional_services ?? []).filter(
    (s: string) => !["bedrock", "rds", "ec2", "vpc"].includes(String(s).toLowerCase()),
  );

  const nodes: Node[] = [
    { id: "entry", type: "custom", position: { x: 250, y: 0 }, data: { label: `Internet (${region})`, icon: "globe" } },
    {
      id: "vpc",
      type: "custom",
      position: { x: 250, y: 120 },
      data: { label: `VPC (${architectureJson?.public ? "public" : "private"})`, icon: "cloud" },
    },
    { id: "ec2", type: "custom", position: { x: 120, y: 250 }, data: { label: `EC2 x${ec2Count} (${ec2Type})`, icon: "server" } },
  ];

  const edges: Edge[] = [
    {
      id: "e-entry-vpc",
      source: "entry",
      target: "vpc",
      markerEnd: { type: MarkerType.ArrowClosed, color: "#487bff" },
      style: { stroke: "#487bff", strokeWidth: 1.6 },
    },
    {
      id: "e-vpc-ec2",
      source: "vpc",
      target: "ec2",
      markerEnd: { type: MarkerType.ArrowClosed, color: "#58e1c1" },
      style: { stroke: "#58e1c1", strokeWidth: 1.6 },
    },
  ];

  if (rdsEnabled) {
    nodes.push({
      id: "rds",
      type: "custom",
      position: { x: 380, y: 250 },
      data: { label: `RDS (${rdsEngine})`, icon: "database" },
    });
    edges.push({
      id: "e-ec2-rds",
      source: "ec2",
      target: "rds",
      markerEnd: { type: MarkerType.ArrowClosed, color: "#8ab0ff" },
      style: { stroke: "#8ab0ff", strokeWidth: 1.6 },
    });
  }

  if (bedrockEnabled) {
    nodes.push({
      id: "bedrock",
      type: "custom",
      position: { x: 250, y: 380 },
      data: { label: `Bedrock (${bedrockModel})`, icon: "bot" },
    });
    edges.push({
      id: "e-ec2-bedrock",
      source: "ec2",
      target: "bedrock",
      markerEnd: { type: MarkerType.ArrowClosed, color: "#ffb453" },
      style: { stroke: "#ffb453", strokeWidth: 1.6 },
    });
  }

  additionalServices.forEach((service: string, idx: number) => {
    const id = `svc-${service}-${idx}`;
    nodes.push({
      id,
      type: "custom",
      position: { x: 60 + (idx % 4) * 170, y: 500 + Math.floor(idx / 4) * 110 },
      data: { label: String(service).toUpperCase(), icon: "cloud" },
    });
    edges.push({
      id: `e-ec2-${id}`,
      source: "ec2",
      target: id,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
      style: { stroke: "#94a3b8", strokeWidth: 1.25, strokeDasharray: "4 4" },
    });
  });

  return { nodes, edges };
}

export function ArchitectureDiagram({
  generationStatus,
  architectureJson,
  rationale,
}: ArchitectureDiagramProps) {
  const graph = useMemo(() => buildGraph(architectureJson), [architectureJson]);

  if (generationStatus === "idle") {
    return (
      <div className="flex h-[640px] items-center justify-center bg-[linear-gradient(180deg,#fbfdff_0%,#f4f7fb_100%)]">
        <Empty>
          <EmptyMedia variant="icon">
            <Cloud className="h-6 w-6" strokeWidth={1.8} />
          </EmptyMedia>
          <EmptyTitle>아키텍처 다이어그램</EmptyTitle>
          <EmptyDescription>
            요구사항 분석이 끝나면 연결 구조와 주요 AWS 리소스를 시각적으로 보여줍니다.
          </EmptyDescription>
        </Empty>
      </div>
    );
  }

  if (generationStatus === "analyzing") {
    return (
      <div className="flex h-[640px] items-center justify-center bg-[linear-gradient(180deg,#fbfdff_0%,#f4f7fb_100%)]">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 animate-spin rounded-full border-2 border-[#d9e4f2] border-t-[#487bff]" />
          <p className="mt-4 text-sm font-semibold text-[#122033]">아키텍처를 구성하는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[640px] w-full flex-col bg-[linear-gradient(180deg,#fbfdff_0%,#f4f7fb_100%)]">
      <div className="min-h-0 flex-1">
        <ReactFlow
          nodes={graph.nodes}
          edges={graph.edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          proOptions={{ hideAttribution: true }}
          className="bg-transparent"
        >
          <Background color="#dbe7f5" gap={20} size={1} />
          <Controls
            className="!rounded-2xl !border-[#d9e4f2] !bg-white/95 !shadow-[0_10px_24px_rgba(72,123,255,0.12)] [&>button]:!border-[#e4edf8] [&>button]:!bg-white [&>button]:!text-[#65748b]"
            showInteractive={false}
          />
        </ReactFlow>
      </div>
      {rationale ? (
        <div className="border-t border-[#e4edf8] bg-white/72 px-5 py-4 text-xs">
          <p className="font-semibold text-[#122033]">AI 설계 이유</p>
          {rationale.summary ? <p className="mt-1 text-[#65748b]">{rationale.summary}</p> : null}
          {rationale.intentPoints?.length ? (
            <p className="mt-2 text-[#314257]">요구 인식: {rationale.intentPoints.join(" / ")}</p>
          ) : null}
          {rationale.designPoints?.length ? (
            <p className="mt-1 text-[#314257]">적용 설계: {rationale.designPoints.join(" / ")}</p>
          ) : null}
          {rationale.whyBetter?.length ? (
            <p className="mt-1 font-medium text-[#2f64ef]">개선 이유: {rationale.whyBetter.join(" / ")}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
