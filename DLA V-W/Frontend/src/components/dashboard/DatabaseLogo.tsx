interface DatabaseLogoProps {
  name: string;
  size?: number;
}
 
const logos: Record<string, string> = {
  "sql server": "/logos/microsoftsqlserver.png",
  mysql: "/logos/mysql.png",
  postgres: "/logos/postgresql.png",
  postgresql: "/logos/postgresql.png",
  mongodb: "/logos/mongodb.png",
  oracle: "/logos/oracle.png",
  snowflake: "/logos/Snowflake.png",
  bigquery: "/logos/bigquery.png",
  redshift: "/logos/redshift.png",
  databricks: "/logos/databricks.png",
  aws: "/logos/aws.png",
  azure: "/logos/azure.png",
};
 
const DatabaseLogo = ({ name, size = 28 }: DatabaseLogoProps) => {
  let key = name.toLowerCase();
 
  if (key.includes("sqlserver") || key.includes("sql server")) {
    key = "sql server";
  }

  if (key.includes("postgres")) {
    key = "postgres";
  }
 
  const logoPath = logos[key];
 
  // fallback if logo not found
  if (!logoPath) {
    return (
      <div
        className="rounded-lg bg-gray-100 flex items-center justify-center text-xs font-bold"
        style={{ width: size, height: size }}
      >
        {name[0]?.toUpperCase()}
      </div>
    );
  }
 
  return (
    <div
      className="rounded-lg bg-white flex items-center justify-center shadow-sm"
      style={{ width: size, height: size }}
    >
      <img
        src={logoPath}
        alt={name}
        className="object-contain"
        style={{ width: size * 0.8, height: size * 0.8 }}
      />
    </div>
  );
};
 
export default DatabaseLogo;
