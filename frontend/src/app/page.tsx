"use client";

import { useEffect, useState } from "react";
import { getFleetMetrics, getClusters } from "@/lib/api";
import { FleetOverview } from "@/components/FleetOverview";
import { ClusterCard } from "@/components/ClusterCard";
import { Loader } from "lucide-react";

export default function Dashboard() {
  const [fleetMetrics, setFleetMetrics] = useState(null);
  const [clusters, setClusters] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [metricsRes, clustersRes] = await Promise.all([getFleetMetrics(), getClusters()]);
        setFleetMetrics(metricsRes);
        setClusters(clustersRes);
      } catch (err) {
        setError("Failed to fetch data. Please check your backend connection.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const filterClusters = (clusters: any[]) => {
    let filtered = clusters;

    if (filter !== "all") {
      filtered = filtered.filter((c) => c.status?.toLowerCase() === filter.toLowerCase());
    }

    if (searchTerm) {
      filtered = filtered.filter((c) => c.name?.toLowerCase().includes(searchTerm.toLowerCase()));
    }

    return filtered.sort((a, b) => {
      const statusOrder = { CRITICAL: 0, WARNING: 1, NO_DATA: 2, HEALTHY: 3 };
      const aOrder = statusOrder[a.status as keyof typeof statusOrder] || 4;
      const bOrder = statusOrder[b.status as keyof typeof statusOrder] || 4;
      if (aOrder !== bOrder) return aOrder - bOrder;
      return a.name?.localeCompare(b.name) || 0;
    });
  };

  if (loading && !fleetMetrics) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-6 max-w-md">
          <h2 className="text-xl font-bold text-red-400 mb-2">Error</h2>
          <p className="text-red-300">{error}</p>
        </div>
      </div>
    );
  }

  const filteredClusters = filterClusters(clusters);

  return (
    <div className="min-h-screen bg-slate-950 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Fleet Status Dashboard</h1>
          <p className="text-gray-400">Real-time monitoring of your OpenShift clusters</p>
        </div>

        {fleetMetrics && <FleetOverview metrics={fleetMetrics} />}

        <div className="bg-slate-900 rounded-lg p-6 mb-6 border border-slate-700">
          <h2 className="text-xl font-bold text-white mb-4">Clusters</h2>

          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <input
              type="text"
              placeholder="Search cluster..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1 bg-slate-800 border border-slate-700 rounded px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />

            <div className="flex gap-2 flex-wrap">
              {["all", "healthy", "warning", "critical", "no_data"].map((status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  className={`px-4 py-2 rounded text-sm font-semibold transition ${
                    filter === status
                      ? "bg-blue-600 text-white"
                      : "bg-slate-800 text-gray-300 hover:bg-slate-700"
                  }`}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredClusters.map((cluster) => (
              <ClusterCard key={cluster.id} cluster={cluster} />
            ))}
          </div>

          {filteredClusters.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-400">No clusters match your search</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
