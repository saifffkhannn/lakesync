import type { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: number | string;
  icon: ReactNode;
  iconBg: string;
  trend?: string;
  trendUp?: boolean;
  subtitle?: string;
}

const StatCard = ({ title, value, icon, iconBg, trend, trendUp, subtitle }: StatCardProps) => {
  return (
    <div className="bg-white dark:bg-gray-800/80 rounded-2xl border border-gray-100 dark:border-gray-700/50 p-5 
      hover:shadow-lg hover:shadow-gray-200/50 dark:hover:shadow-gray-900/30 transition-all duration-300 
      hover:-translate-y-0.5 group">
      <div className="flex items-start gap-4">
        <div className={`w-12 h-12 rounded-xl ${iconBg} flex items-center justify-center 
          group-hover:scale-110 transition-transform duration-300`}>
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">{title}</p>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">{value}</h3>
          {trend && (
            <p className={`text-xs font-medium mt-1 ${trendUp ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}>
              {trendUp ? "↑" : "↓"} {trend}
            </p>
          )}
          {subtitle && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default StatCard;
