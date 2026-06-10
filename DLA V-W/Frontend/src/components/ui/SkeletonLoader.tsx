const SkeletonRow = () => (
  <tr className="border-t border-gray-100 dark:border-gray-700/50">
    <td className="py-4 px-4">
      <div className="space-y-2">
        <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        <div className="h-3 w-20 bg-gray-100 dark:bg-gray-700/60 rounded animate-pulse" />
      </div>
    </td>
    <td className="py-4 px-4">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-gray-200 dark:bg-gray-700 animate-pulse" />
        <div className="h-4 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        <div className="h-3 w-4 bg-gray-100 dark:bg-gray-700/60 rounded animate-pulse" />
        <div className="w-7 h-7 rounded-lg bg-gray-200 dark:bg-gray-700 animate-pulse" />
        <div className="h-4 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      </div>
    </td>
    <td className="py-4 px-4">
      <div className="h-6 w-20 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse" />
    </td>
    <td className="py-4 px-4">
      <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
    </td>
    <td className="py-4 px-4">
      <div className="h-4 w-14 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
    </td>
    <td className="py-4 px-4">
      <div className="h-5 w-5 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
    </td>
  </tr>
);

const TableSkeleton = ({ rows = 5 }: { rows?: number }) => {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </>
  );
};

export default TableSkeleton;
