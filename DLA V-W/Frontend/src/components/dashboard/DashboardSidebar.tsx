import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Plus,
  Database,
  Link2,
  FileText,
  BookOpen,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import synthlakeLogo from "../../assets/synthlake_logo.png";
 
const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/dashboard", matchPaths: ["/dashboard"] },
  { label: "New Migration", icon: Plus, path: "/config", matchPaths: ["/config", "/mapper", "/progress"] },
  { label: "Migrations", icon: Database, path: "/dashboard", matchPaths: [] },
  { label: "Connections", icon: Link2, path: "/config", matchPaths: ["/config", "/mapper"] },
  { label: "Logs", icon: FileText, path: "/dashboard", matchPaths: [] },
];
 
const supportItems = [
  { label: "Documentation", icon: BookOpen },
  { label: "Help & Support", icon: HelpCircle },
];
 
interface DashboardSidebarProps {
  totalMigrations?: number;
  maxMigrations?: number;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}
 
const DashboardSidebar = ({
  isCollapsed,
  onToggleCollapse,
}: DashboardSidebarProps) => {
  const navigate = useNavigate();
  const location = useLocation();
 
  return (
    <aside
      className={`min-h-screen bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800
        flex flex-col justify-between transition-[width] duration-300 ease-out ${isCollapsed ? "w-[92px]" : "w-[280px]"}`}
    >
     
      {/* Top */}
      <div className={`${isCollapsed ? "p-4" : "p-5"} transition-all duration-300`}>
        {/* Logo Section */}
        <div className="group relative mb-8">
          {/* Logo Clickable */}
          <div
            onClick={() => navigate("/dashboard")}
            className={`cursor-pointer w-full rounded-2xl transition-all duration-300 flex items-center
              ${isCollapsed ? "px-1 py-2 justify-center" : "px-2 py-3 justify-between"}`}
          >
            <img
              src={isCollapsed ? synthlakeLogo : "/logo.png"}
              alt="Synthlake AI"
              className={`w-auto object-contain transition-all duration-500 ease-in-out
                ${isCollapsed 
                  ? "h-12 group-hover:opacity-20 group-hover:scale-90 group-hover:blur-[1px]" 
                  : "h-14"}`}
            />
            
            {/* Toggle Button for Expanded State - Always Visible */}
            {!isCollapsed && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleCollapse();
                }}
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-50 dark:bg-gray-800/50
                  border border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500
                  hover:text-blue-600 dark:hover:text-blue-400 hover:border-blue-200 dark:hover:border-blue-900/50 
                  hover:bg-white dark:hover:bg-gray-800 transition-all duration-200"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Toggle Button for Collapsed State - Only on Hover */}
          {isCollapsed && (
            <div
              className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleCollapse();
                }}
                className="flex h-10 w-10 items-center justify-center rounded-xl bg-white dark:bg-gray-900/90
                  border border-blue-200 dark:border-blue-800 shadow-lg shadow-blue-500/10 text-blue-600 dark:text-blue-400
                  hover:scale-110 active:scale-95 transition-all duration-200"
              >
                <ChevronRight className="h-6 w-6" />
              </button>
            </div>
          )}
        </div>
 
        {/* Nav Items */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = item.matchPaths.includes(location.pathname);
            return (
              <button
                key={item.label}
                id={`nav-${item.label.toLowerCase().replace(/\s/g, "-")}`}
                onClick={() => navigate(item.path)}
                title={isCollapsed ? item.label : undefined}
                className={`w-full relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-300
                  ${isCollapsed ? "justify-center" : ""}
                  ${isActive
                    ? "bg-blue-50/50 dark:bg-blue-900/10 text-blue-600 dark:text-blue-400 shadow-[0_0_20px_-5px_rgba(59,130,246,0.15)] dark:shadow-[0_0_20px_-5px_rgba(59,130,246,0.1)]"
                    : "text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200"
                  }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="active-nav-indicator"
                    className="absolute left-0 w-1 h-6 bg-blue-600 dark:bg-blue-500 rounded-r-full"
                  />
                )}
                <item.icon className={`w-[18px] h-[18px] shrink-0 transition-transform duration-300 ${isActive ? "scale-110" : ""}`} />
                <span
                  className={`overflow-hidden whitespace-nowrap transition-all duration-200 ${
                    isCollapsed ? "max-w-0 opacity-0" : "max-w-[160px] opacity-100"
                  }`}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>
 
        {/* Support */}
        <div className="mt-8 pt-6 border-t border-gray-100 dark:border-gray-800">
          {!isCollapsed && (
            <p className="text-[10px] uppercase font-semibold text-gray-300 dark:text-gray-600 tracking-wider mb-3 px-3">
              Support
            </p>
          )}
          {supportItems.map((item) => (
            <button
              key={item.label}
              title={isCollapsed ? item.label : undefined}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-gray-500 dark:text-gray-400
                ${isCollapsed ? "justify-center" : ""}
                hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200 transition-all duration-200`}
            >
              <item.icon className={`w-[18px] h-[18px] shrink-0 ${isCollapsed ? "mx-auto" : ""}`} />
              <span
                className={`overflow-hidden whitespace-nowrap transition-all duration-200 ${
                  isCollapsed ? "max-w-0 opacity-0" : "max-w-[160px] opacity-100"
                }`}
              >
                {item.label}
              </span>
            </button>
          ))}
        </div>
      </div>
 
      {/* Bottom — Plan Card */}
      {/* <div className="p-5">
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-2xl p-4 border border-gray-100 dark:border-gray-700/50"> */}
          {/* <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-400 dark:text-gray-500">Current Plan</span>
          </div> */}
          {/* <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-bold text-gray-800 dark:text-white">Free Plan</span>
            <button className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 transition-colors">
              Upgrade
            </button>
          </div> */}
          {/* Usage bar */}
          {/* <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-2">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-500"
              style={{ width: `${usagePercent}%` }}
            />
          </div> */}
          {/* <p className="text-xs text-gray-400 dark:text-gray-500">
            {totalMigrations} of {maxMigrations} Migrations Used
          </p> */}
        {/* </div>
      </div> */}
    </aside>
  );
};
 
export default DashboardSidebar;
