import { useState, useRef, useEffect, type ReactNode } from "react";
import { Search, Moon, Sun, Bell, Check, Info, AlertCircle, X } from "lucide-react";
import { useTheme } from "../../contexts/ThemeContext";
import UserMenu from "./UserMenu";
import { motion, AnimatePresence } from "framer-motion";

interface Notification {
  id: number;
  title: string;
  message: string;
  type: string;
  time: string;
  read: boolean;
}

interface DashboardNavProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  searchPlaceholder?: string;
  rightSlot?: ReactNode;
  showSearch?: boolean;
}

const DashboardNav = ({
  searchTerm,
  onSearchChange,
  searchPlaceholder = "Search migrations, jobs, tables...",
  rightSlot,
  showSearch = true,
}: DashboardNavProps) => {
  const { isDark, toggleTheme } = useTheme();
  const [showNotifications, setShowNotifications] = useState(false);
  const notificationRef = useRef<HTMLDivElement>(null);

  // Sync with localStorage
  const [notifications, setNotifications] = useState<Notification[]>(() => {
    const saved = localStorage.getItem("notifications");
    return saved ? JSON.parse(saved) : [
      { id: 1, title: "System Ready", message: "Metadata synchronization complete.", type: "info", time: "10m ago", read: true },
      { id: 2, title: "Welcome", message: "Synthlake Data Migration is ready.", type: "info", time: "1h ago", read: true },
    ];
  });

  const unreadCount = notifications.filter((n: Notification) => !n.read).length;

  useEffect(() => {
    const syncNotifications = () => {
      const saved = localStorage.getItem("notifications");
      if (saved) setNotifications(JSON.parse(saved));
    };

    const handleClick = (e: MouseEvent) => {
      if (notificationRef.current && !notificationRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };

    window.addEventListener("notificationsUpdated", syncNotifications);
    document.addEventListener("mousedown", handleClick);
    return () => {
      window.removeEventListener("notificationsUpdated", syncNotifications);
      document.removeEventListener("mousedown", handleClick);
    };
  }, []);

  const markAllRead = () => {
    const next = notifications.map((n: Notification) => ({ ...n, read: true }));
    setNotifications(next);
    localStorage.setItem("notifications", JSON.stringify(next));
  };

  const removeNotification = (id: number) => {
    const next = notifications.filter((n: any) => n.id !== id);
    setNotifications(next);
    localStorage.setItem("notifications", JSON.stringify(next));
  };

  return (
    <header className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-gray-100 dark:border-gray-800 
      px-6 py-3 flex justify-between items-center sticky top-0 z-40 transition-colors duration-300">
      
      {/* Search */}
      {showSearch ? (
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-300 dark:text-gray-600 w-4 h-4" />
          <input
            id="dashboard-search"
            type="text"
            placeholder={searchPlaceholder}
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-10 pr-16 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700/50 
              rounded-xl text-sm text-gray-700 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500
              focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 dark:focus:border-blue-600 
              transition-all duration-200"
          />
          {/* Keyboard hint */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 
              rounded text-[10px] font-medium text-gray-400 dark:text-gray-500">
              ⌘
            </kbd>
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 
              rounded text-[10px] font-medium text-gray-400 dark:text-gray-500">
              K
            </kbd>
          </div>
        </div>
      ) : (
        <div /> // Spacer
      )}

      {/* Right side */}
      <div className="flex items-center gap-2">
        {/* Dark mode toggle */}
        <button
          id="theme-toggle"
          onClick={toggleTheme}
          className="p-2.5 rounded-xl text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 
            hover:text-gray-600 dark:hover:text-gray-300 transition-all duration-200"
          aria-label="Toggle theme"
        >
          {isDark ? <Sun className="w-[18px] h-[18px]" /> : <Moon className="w-[18px] h-[18px]" />}
        </button>

        {/* Notifications */}
        <div className="relative" ref={notificationRef}>
          <button
            id="notifications-bell"
            onClick={() => setShowNotifications(!showNotifications)}
            className={`p-2.5 rounded-xl transition-all duration-200 relative
              ${showNotifications 
                ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400" 
                : "text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-300"
              }`}
          >
            <Bell className="w-[18px] h-[18px]" />
            {unreadCount > 0 && (
              <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white dark:ring-gray-900 animate-pulse" />
            )}
          </button>

          <AnimatePresence>
            {showNotifications && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 z-50 overflow-hidden"
              >
                <div className="p-4 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-gray-50/50 dark:bg-gray-800/30">
                  <h3 className="font-bold text-sm text-gray-900 dark:text-white">Notifications</h3>
                  {unreadCount > 0 && (
                    <button onClick={markAllRead} className="text-[10px] font-bold text-blue-600 dark:text-blue-400 hover:underline">
                      Mark all read
                    </button>
                  )}
                </div>

                <div className="max-h-[360px] overflow-y-auto custom-scrollbar">
                  {notifications.length > 0 ? (
                    <div className="divide-y divide-gray-50 dark:divide-gray-800">
                      {notifications.map((n: Notification) => (
                        <div key={n.id} className={`p-4 hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors relative group ${!n.read ? "bg-blue-50/20 dark:bg-blue-900/5" : ""}`}>
                          <div className="flex gap-3">
                            <div className={`mt-0.5 w-8 h-8 rounded-full flex items-center justify-center shrink-0 
                              ${n.type === 'success' ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-600' : 
                                n.type === 'error' ? 'bg-red-100 dark:bg-red-900/20 text-red-600' : 
                                'bg-blue-100 dark:bg-blue-900/20 text-blue-600'}`}>
                              {n.type === 'success' ? <Check size={14} /> : n.type === 'error' ? <AlertCircle size={14} /> : <Info size={14} />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className={`text-xs font-bold ${!n.read ? "text-gray-900 dark:text-white" : "text-gray-600 dark:text-gray-400"}`}>{n.title}</p>
                              <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2 leading-relaxed">{n.message}</p>
                              <span className="text-[10px] text-gray-400 dark:text-gray-500 mt-2 block">{n.time}</span>
                            </div>
                            <button 
                              onClick={() => removeNotification(n.id)}
                              className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-all"
                            >
                              <X size={12} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-12 px-4 text-center">
                      <Bell size={32} className="mx-auto text-gray-200 dark:text-gray-800 mb-3" />
                      <p className="text-xs text-gray-400 dark:text-gray-600 font-medium">All caught up!</p>
                    </div>
                  )}
                </div>

                {notifications.length > 0 && (
                  <div className="p-3 bg-gray-50/50 dark:bg-gray-800/30 border-t border-gray-100 dark:border-gray-800 text-center">
                    <button className="text-[11px] font-bold text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
                      View all activity
                    </button>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Divider */}
        <div className="w-px h-8 bg-gray-100 dark:bg-gray-800 mx-1" />

        {rightSlot}

        {/* User Menu */}
        <UserMenu />
      </div>
    </header>
  );
};

export default DashboardNav;
