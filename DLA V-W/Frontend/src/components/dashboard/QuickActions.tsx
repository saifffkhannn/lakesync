import { useNavigate } from "react-router-dom";
import {
  Plus,
  Link2,
  FileText,
  ChevronRight,
} from "lucide-react";

const actions = [
  {
    label: "Create New Migration",
    description: "Start a new data migration",
    icon: Plus,
    iconBg: "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400",
    path: "/config",
  },
  {
    label: "Add Connection",
    description: "Connect your data sources",
    icon: Link2,
    iconBg: "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400",
    path: "/config",
  },
  {
    label: "View Logs",
    description: "Check system logs",
    icon: FileText,
    iconBg: "bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400",
    path: "/dashboard",
  },
];

const QuickActions = () => {
  const navigate = useNavigate();

  return (
    <div className="bg-white dark:bg-gray-800/80 rounded-2xl border border-gray-100 dark:border-gray-700/50 
      overflow-hidden transition-colors duration-300">
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/50">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">Quick Actions</h3>
      </div>

      <div className="p-3 space-y-1">
        {actions.map((action) => (
          <button
            key={action.label}
            id={`quick-action-${action.label.toLowerCase().replace(/\s/g, "-")}`}
            onClick={() => navigate(action.path)}
            className="w-full flex items-center gap-3 px-3 py-3 rounded-xl 
              hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-all duration-200 group"
          >
            <div className={`w-10 h-10 rounded-xl ${action.iconBg} flex items-center justify-center 
              group-hover:scale-105 transition-transform duration-200`}>
              <action.icon className="w-[18px] h-[18px]" />
            </div>
            <div className="flex-1 text-left">
              <p className="text-sm font-medium text-gray-800 dark:text-white">{action.label}</p>
              <p className="text-xs text-gray-400 dark:text-gray-500">{action.description}</p>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-300 dark:text-gray-600 group-hover:text-gray-400 
              group-hover:translate-x-0.5 transition-all duration-200" />
          </button>
        ))}
      </div>
    </div>
  );
};

export default QuickActions;
