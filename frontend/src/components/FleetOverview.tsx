"use client";

import React from "react";
import { AlertTriangle, Zap, Server, Activity } from "lucide-react";

interface FleetOverviewProps {
  metrics: any;
}

export function FleetOverview({ metrics }: FleetOverviewProps) {
  if (!metrics) return null;

  const statusColor = {
    HEALTHY: "bg-green-500",
    WARNING: "bg-yellow-500",
    CRITICAL: "bg-red-500",
  };

  return (
    <div className="bg-slate-900 rounded-lg p-6 mb-6 border border-slate-700">
      <h2 className="text-2xl font-bold text-white mb-6">OPENSHIFT FLEET STATUS</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-slate-800 rounded p-4 border border-slate-700">
          <div className="text-gray-400 text-sm mb-1">Clusters</div>
          <div className="text-3xl font-bold text-white">{metrics.clusters.total}</div>
        </div>

        <div className="bg-slate-800 rounded p-4 border border-slate-700">
          <div className="text-gray-400 text-sm mb-1">Nodes</div>
          <div className="text-3xl font-bold text-white">{metrics.nodes.total}</div>
        </div>

        <div className="bg-slate-800 rounded p-4 border border-slate-700">
          <div className="text-gray-400 text-sm mb-1">Critical Alerts</div>
          <div className="text-3xl font-bold text-red-400">{metrics.alerts.critical}</div>
        </div>

        <div className="bg-slate-800 rounded p-4 border border-slate-700">
          <div className="text-gray-400 text-sm mb-1">Avg CPU</div>
          <div className="text-3xl font-bold text-white">
            {metrics.cpu.average_percent?.toFixed(1) || "N/A"}%
          </div>
        </div>

        <div className="bg-slate-800 rounded p-4 border border-slate-700">
          <div className="text-gray-400 text-sm mb-1">Avg Memory</div>
          <div className="text-3xl font-bold text-white">
            {metrics.memory.average_percent?.toFixed(1) || "N/A"}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mt-6">
        <div className="text-center p-3 bg-slate-800 rounded border border-slate-700">
          <div className="text-sm text-gray-400 mb-1">Healthy</div>
          <div className="text-2xl font-bold text-green-400">{metrics.clusters.healthy}</div>
        </div>
        <div className="text-center p-3 bg-slate-800 rounded border border-slate-700">
          <div className="text-sm text-gray-400 mb-1">Warning</div>
          <div className="text-2xl font-bold text-yellow-400">{metrics.clusters.warning}</div>
        </div>
        <div className="text-center p-3 bg-slate-800 rounded border border-slate-700">
          <div className="text-sm text-gray-400 mb-1">Critical</div>
          <div className="text-2xl font-bold text-red-400">{metrics.clusters.critical}</div>
        </div>
        <div className="text-center p-3 bg-slate-800 rounded border border-slate-700">
          <div className="text-sm text-gray-400 mb-1">No Data</div>
          <div className="text-2xl font-bold text-gray-400">{metrics.clusters.no_data}</div>
        </div>
        <div className="text-center p-3 bg-slate-800 rounded border border-slate-700">
          <div className="text-sm text-gray-400 mb-1">Ready Nodes</div>
          <div className="text-2xl font-bold text-green-400">{metrics.nodes.ready}</div>
        </div>
        <div className="text-center p-3 bg-slate-800 rounded border border-slate-700">
          <div className="text-sm text-gray-400 mb-1">Not Ready</div>
          <div className="text-2xl font-bold text-red-400">{metrics.nodes.not_ready}</div>
        </div>
      </div>
    </div>
  );
}
