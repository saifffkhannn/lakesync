import React, { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, Home } from "lucide-react";
import DashboardSidebar from "./DashboardSidebar";
import DashboardNav from "./DashboardNav";

const BREADCRUMB_MAP: Record<string, string> = {
  "/dashboard": "Home",
  "/config": "Connections",
  "/mapper": "Source Mapper",
  "/progress": "Pipeline Monitor",
};

const PATH_HIERARCHY: Record<string, string[]> = {
  "/dashboard": ["/dashboard"],
  "/config": ["/dashboard", "/config"],
  "/mapper": ["/dashboard", "/config", "/mapper"],
  "/progress": ["/dashboard", "/config", "/mapper", "/progress"],
};

interface DashboardLayoutProps {
  children: React.ReactNode;
  showSearch?: boolean;
  searchTerm?: string;
  onSearchChange?: (term: string) => void;
}

const DashboardLayout = ({ 
  children, 
  showSearch = true,
  searchTerm: externalSearchTerm,
  onSearchChange: externalOnSearchChange
}: DashboardLayoutProps) => {
  const location = useLocation();
  
  // Persistence for sidebar
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    // Directly expand on Dashboard, otherwise remember old state
    if (location.pathname === "/dashboard") return false;
    const saved = localStorage.getItem("sidebar-collapsed");
    return saved === "true";
  });

  const [internalSearchTerm, setInternalSearchTerm] = useState("");

  // Logic to auto-expand on Dashboard
  React.useEffect(() => {
    if (location.pathname === "/dashboard") {
      setIsSidebarCollapsed(false);
    }
  }, [location.pathname]);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(prev => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed", String(next));
      return next;
    });
  };

  const searchTerm = externalSearchTerm !== undefined ? externalSearchTerm : internalSearchTerm;
  const setSearchTerm = externalOnSearchChange || setInternalSearchTerm;

  const currentCrumbs = PATH_HIERARCHY[location.pathname] || ["/dashboard"];

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-950 transition-colors duration-300">
      {/* SIDEBAR */}
      <DashboardSidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={toggleSidebar}
      />

      {/* MAIN */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* TOP NAV */}
        <DashboardNav 
          searchTerm={searchTerm} 
          onSearchChange={setSearchTerm}
          searchPlaceholder={showSearch ? undefined : "..."}
          showSearch={showSearch}
        />

        {/* CONTENT */}
        <div className="flex-1 overflow-y-auto p-6 transition-[padding] duration-300 ease-out lg:p-8 custom-scrollbar">
          <div className={`mx-auto w-full transition-[max-width] duration-300 ease-out ${isSidebarCollapsed ? "max-w-[1520px]" : "max-w-[1380px]"}`}>
            
            {/* Breadcrumbs */}
            <nav className="flex items-center gap-2 mb-6 text-xs font-medium text-gray-400 dark:text-gray-500">
              {currentCrumbs.map((path, idx) => (
                <React.Fragment key={path}>
                  {idx > 0 && <ChevronRight size={12} className="mx-0.5 opacity-50" />}
                  {idx === currentCrumbs.length - 1 ? (
                    <span className="text-gray-900 dark:text-white font-bold">
                      {BREADCRUMB_MAP[path]}
                    </span>
                  ) : (
                    <Link to={path} className="hover:text-blue-600 transition-colors flex items-center gap-1">
                       {path === "/dashboard" && <Home size={12} />} {BREADCRUMB_MAP[path]}
                    </Link>
                  )}
                </React.Fragment>
              ))}
            </nav>

            {/* Page Content with Transition */}
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                {children}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardLayout;
