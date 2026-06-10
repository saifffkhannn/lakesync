import { useState, useRef, useEffect } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { User, LogOut, ChevronDown } from "lucide-react";

const UserMenu = () => {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const initials = user?.initials || "U";
  const name = user?.name || "User";
  const email = user?.email || "user@example.com";

  return (
    <div className="relative" ref={menuRef}>
      {/* Trigger */}
      <button
        id="user-menu-button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2.5 px-2 py-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700/50 
          transition-colors duration-200 cursor-pointer"
      >
        <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-xl 
          flex items-center justify-center text-sm font-semibold shadow-md shadow-blue-500/20">
          {initials}
        </div>
        <div className="hidden lg:block text-left">
          <p className="text-sm font-semibold text-gray-800 dark:text-white leading-tight">{name}</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 leading-tight">{email}</p>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-xl shadow-xl 
          shadow-gray-200/50 dark:shadow-gray-900/50 border border-gray-100 dark:border-gray-700/50 
          py-2 z-50 animate-fadeIn">
          
          {/* User info */}
          <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700/50">
            <p className="text-sm font-semibold text-gray-800 dark:text-white">{name}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{email}</p>
          </div>

          {/* Items */}
          <div className="py-1">
            <button
              id="user-menu-profile"
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-600 dark:text-gray-300 
                hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              onClick={() => setOpen(false)}
            >
              <User className="w-4 h-4" />
              Profile
            </button>
          </div>

          <div className="border-t border-gray-100 dark:border-gray-700/50 py-1">
            <button
              id="user-menu-logout"
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-500 
                hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              onClick={() => {
                setOpen(false);
                logout();
              }}
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserMenu;
