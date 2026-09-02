"use client";

import React from "react";
import { AlertTriangle, CheckCircle, AlertCircle, HelpCircle } from "lucide-react";
import Link from "next/link";

interface ClusterCardProps {
  cluster: any;
}

export function ClusterCard({ cluster }: ClusterCardProps) {
  const statusConfig = {
    HEALTHY: { color: "border-green-500", icon: CheckCircle, label: "HEALTHY", bgColor: "bg-green-900/20" },
    WARNING: { color: "border-yellow-500", icon: AlertCircle, label: "WARNING", bgColor: "bg-yellow-900/20" },
    CRITICAL: { color: "border-red-500", icon: AlertTriangle, label: "CRITICAL", bgColor: "bg-red-900/20" },
    NO_DATA: { color: "border-gray-500", icon: HelpCircle, label: "NO_DATA", bgColor: "bg-gray-900/20" },
  };

  const config = statusConfig[cluster.status as keyof typeof statusConfig] || statusConfig.NO_DATA;
  const Icon = config.icon;

  const cpuClass = (cpu: number | null) => {
    if (!cpu) return "text-gray-400";
    if (cpu >= 90) return "text-red-400";
    if (cpu >= 85) return "text-orange-400";
    if (cpu >= 70) return "text-yellow-400";
    return "text-green-400";
  };

  const memoryClass = (mem: number | null) => {
    if (!mem) return "text-gray-400";
    if (mem >= 90) return "text-red-400";
    if (mem >= 85) return "text-orange-400";
    if (mem >= 75) return "text-yellow-400";
    return "text-green-400";
  };

  return (
    <Link href={`/clusters/${cluster.name}`}>
      <div className={`${config.bgColor} border ${config.color} rounded-lg p-5 cursor-pointer hover:opacity-80 transition`}>
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-bold text-white">{cluster.name}</h3>
            <p className="text-sm text-gray-400 mt-1">OpenShift {cluster.version || "Unknown"}</p>
          </div>
          <div className="flex items-center gap-2">
            <Icon className="w-5 h-5" color={config.color.split("-")[1] === "green" ? "#22c55e" : config.color.split("-")[1] === "yellow" ? "#eab308" : "#ef4444"} />
            <span className="text-sm font-semibold text-white">{config.label}</span>
          </div>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div>
              <span className="text-gray-400">Nodes:</span>
              <div className="text-white font-semibold">{cluster.nodes.total}</div>
            </div>
            <div>
              <span className="text-gray-400">Ready:</span>
              <div className="text-green-400 font-semibold">{cluster.nodes.ready}</div>
            </div>
            <div>
              <span className="text-gray-400">Sched:</span>
              <div className="text-white font-semibold">{cluster.nodes.schedulable}</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-800/50 rounded p-2">
              <div className="text-xs text-gray-400 mb-1">CPU</div>
              <div className={`text-lg font-bold ${cpuClass(cluster.cpu.average_percent)}`}>
                {cluster.cpu.average_percent?.toFixed(1) || "N/A"}%
              </div>
              <div className="text-xs text-gray-500">Avg</div>
            </div>
            <div className="bg-slate-800/50 rounded p-2">
              <div className="text-xs text-gray-400 mb-1">Peak CPU</div>
              <div className={`text-lg font-bold ${cpuClass(cluster.cpu.peak_percent)}`}>
                {cluster.cpu.peak_percent?.toFixed(1) || "N/A"}%
              </div>
              <div className="text-xs text-gray-500">{cluster.cpu.highest_node}</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-800/50 rounded p-2">
              <div className="text-xs text-gray-400 mb-1">Memory</div>
              <div className={`text-lg font-bold ${memoryClass(cluster.memory.average_percent)}`}>
                {cluster.memory.average_percent?.toFixed(1) || "N/A"}%
              </div>
              <div className="text-xs text-gray-500">Avg</div>
            </div>
            <div className="bg-slate-800/50 rounded p-2">
              <div className="text-xs text-gray-400 mb-1">Peak Mem</div>
              <div className={`text-lg font-bold ${memoryClass(cluster.memory.peak_percent)}`}>
                {cluster.memory.peak_percent?.toFixed(1) || "N/A"}%
              </div>
              <div className="text-xs text-gray-500">{cluster.memory.highest_node}</div>
            </div>
          </div>

          <div className="flex justify-between items-center text-sm">
            <div className="flex gap-2">
              <span className="text-red-400">🔴 {cluster.alerts.critical}</span>
              <span className="text-yellow-400">🟡 {cluster.alerts.warning}</span>
            </div>
            <span className="text-gray-500 text-xs">
              {cluster.metrics.last_received ? new Date(cluster.metrics.last_received).toLocaleTimeString() : "N/A"}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
