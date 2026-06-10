import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  Database,
  CheckCircle,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import DashboardLayout from "../components/dashboard/DashboardLayout";
import StatCard from "../components/dashboard/StatCard";
import MigrationsTable from "../components/dashboard/MigrationsTable";
import type { Migration } from "../components/dashboard/MigrationsTable";
import QuickActions from "../components/dashboard/QuickActions";
import { showToast } from "../components/ui/Toast";
 
const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
 
  const [migrations, setMigrations] = useState<Migration[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
 
  // 🔄 Fetch data (REAL-TIME POLLING)
  useEffect(() => {
    const fetchData = () => {
      fetch("http://localhost:8000/migrations-history")
        .then((res) => res.json())
        .then((historyData) => {
          if (Array.isArray(historyData)) {
            setMigrations(historyData);
          } else {
            setMigrations([]);
          }
          setIsLoading(false);
        })
        .catch((err) => {
          console.error(err);
          setIsLoading(false);
        });
    };
 
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);
 
  const total = migrations.length;
  const completed = migrations.filter((m) => m.status === "Completed").length;
  const failed = migrations.filter((m) => m.status === "Failed").length;
  const inProgress = migrations.filter((m) => m.status === "In Progress").length;
  const successRate = total > 0 ? Math.round((completed / total) * 100) : 0;
  const displayName = user?.name?.split(" ")[0] || "User";
 
  return (
    <DashboardLayout searchTerm={searchTerm} onSearchChange={setSearchTerm}>
      {/* HEADER */}
      <div className="mb-8">
        <p className="text-sm font-semibold text-blue-600 dark:text-blue-400 mb-1 tracking-wide uppercase">
          Welcome back, {displayName}!
        </p>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
              Dashboard
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Monitor and manage your data migrations
            </p>
          </div>
          <button
            id="new-migration-button"
            onClick={() => navigate("/config")}
            className="bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 
              text-white px-5 py-2.5 rounded-xl flex items-center gap-2 text-sm font-semibold
              shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 
              hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200"
          >
            <Plus className="w-4 h-4" /> New Migration
          </button>
        </div>
      </div>

      {/* STATS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Total Migrations"
          value={total}
          icon={<Database className="w-5 h-5 text-blue-600" />}
          iconBg="bg-blue-50 dark:bg-blue-900/20"
          trend=""
          trendUp={true}
        />
        <StatCard
          title="Completed"
          value={completed}
          icon={<CheckCircle className="w-5 h-5 text-emerald-600" />}
          iconBg="bg-emerald-50 dark:bg-emerald-900/20"
          subtitle={`${successRate}% Success Rate`}
        />
        <StatCard
          title="In Progress"
          value={inProgress}
          icon={<Clock className="w-5 h-5 text-amber-600" />}
          iconBg="bg-amber-50 dark:bg-amber-900/20"
          subtitle={inProgress > 0 ? `${inProgress} Running Now` : undefined}
        />
        <StatCard
          title="Failed"
          value={failed}
          icon={<AlertTriangle className="w-5 h-5 text-red-500" />}
          iconBg="bg-red-50 dark:bg-red-900/20"
          subtitle={failed > 0 ? "View Logs" : undefined}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <MigrationsTable
            migrations={migrations}
            searchTerm={searchTerm}
            isLoading={isLoading}
            onViewLogs={(m) => showToast(`Viewing logs for ${m.name}`, "info")}
            onRetry={(m) => showToast(`Retrying migration: ${m.name}`, "info")}
            onDelete={(m) => showToast(`Deleted migration: ${m.name}`, "error")}
          />
        </div>
        <div>
          <QuickActions />
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
