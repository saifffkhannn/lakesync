import { useEffect, useState, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import { Search, Database, Table, Check, ArrowLeft, Play } from "lucide-react"
import DashboardLayout from "../components/dashboard/DashboardLayout"
import ThemedSelect from "../components/ThemedSelect"

const SourceMapper = () => {

  const navigate = useNavigate()

  const [tables, setTables] = useState<any[]>([])
  const [selectedSchema, setSelectedSchema] = useState("")
  const [selectedTables, setSelectedTables] = useState<string[]>([])
  const [search, setSearch] = useState("")
  const [toast, setToast] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  // Config retrieved from localStorage
  const source = (localStorage.getItem("selectedSource") || "").toLowerCase()
  const cloud = (localStorage.getItem("selectedCloud") || "").toLowerCase()
  const target = (localStorage.getItem("selectedTarget") || "").toLowerCase()

  useEffect(() => {
    if (source && cloud && target) {
      fetchMetadata()
    }
  }, [source, cloud, target])

  const fetchMetadata = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/fetch-metadata?source=${source}&cloud=${cloud}&target=${target}`)
      const data = await response.json()
      if (response.ok) {
        const mappedTables = data.map((t: any) => ({
          database: t.DB_NAME || t.DATABASE || t.database || "",
          schema: t.TABLE_SCHEMA || t.SCHEMA || t.schema,
          table: t.TABLE_NAME || t.TABLE || t.table,
          primaryKey: t.PRIMARY_KEY_COLUMNS || t.PRIMARY_KEY || t.primaryKey || ""
        }))
        setTables(mappedTables)
      } else {
        setToast(`Error: ${data.detail || "Failed to fetch metadata"}`)
      }
    } catch (err) {
      setToast("Network error fetching metadata")
    }
    setIsLoading(false)
  }

  const schemas = [...new Set(tables.map(t => t.schema))]

  const filteredTables = useMemo(() => {
    return tables
      .filter(t => t.schema === selectedSchema)
      .filter(t => {
        const tableName = String(t.table || "").toLowerCase();
        const searchLower = search.toLowerCase();
        return tableName.includes(searchLower);
      });
  }, [tables, selectedSchema, search]);


  const toggleTable = (table: string) => {
    if (selectedTables.includes(table)) {
      setSelectedTables(selectedTables.filter(t => t !== table))
    } else {
      setSelectedTables([...selectedTables, table])
    }
  }

  const handleSave = async () => {
    const selections = tables.filter(t => selectedTables.includes(t.table))

    if (selections.length === 0) {
      setToast("Please select at least one table.")
      return
    }

    const invalidSelection = selections.find(
      s => !s.database || !s.schema || !s.table
    )

    if (invalidSelection) {
      setToast("Metadata is missing database name. Fetch metadata again before starting migration.")
      return
    }

    const payload = {
      source: source,
      selections: selections.map(s => ({
        source: source.toUpperCase(),
        database: s.database,
        schema_name: s.schema,
        table: s.table,
        primary_key: s.primaryKey || ""
      }))
    }

    try {
      const response = await fetch("http://localhost:8000/save-metadata", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })

      const res = await response.json()

      if (!response.ok) {
        setToast(`Error saving metadata: ${res.detail}`)
        return
      }

      setToast("Metadata saved. Starting Migration...")
      await handleStartExtraction()

    } catch (err) {
      setToast("Network error saving metadata")
    }
  }

  const handleStartExtraction = async () => {
    const payload = {
      source: source,
      cloud: cloud,
      target: target,
      metadata_filename: `${source}_metadata.csv`
    }

    try {
      const response = await fetch("http://localhost:8000/start-extraction", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })

      const res = await response.json()
      if (response.ok) {
        navigate("/progress")
      } else {
        setToast(`Migration failed: ${res.detail}`)
      }
    } catch (err) {
      setToast("Network error starting Migration")
    }
  }

  const schemaTablesCount = tables.filter(t => t.schema === selectedSchema).length;

  return (
    <DashboardLayout showSearch={true}>
      {/* TOAST */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -20, x: 20 }}
            animate={{ opacity: 1, y: 0, x: 0 }}
            exit={{ opacity: 0, x: 50 }}
            className="fixed top-24 right-5 bg-emerald-600 text-white px-6 py-3 rounded-xl shadow-2xl z-50 flex items-center gap-2"
          >
            <Check size={18} /> {toast}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="max-w-5xl mx-auto">
        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-10 gap-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-1 tracking-tight">
              Source Mapper
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              Select the tables you want to migrate from <span className="font-mono font-bold text-blue-600 uppercase">{source}</span>
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => navigate("/config")}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
            text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
            hover:shadow-md transition-all shadow-sm"
            >
              <ArrowLeft size={16} /> Back to Config
            </button>
          </div>
        </div>

        {/* MAIN CARD */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl shadow-gray-200/50 dark:shadow-black/20 border border-gray-100 dark:border-gray-800 p-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* LEFT COLUMN: Controls */}
            <div className="lg:col-span-1 space-y-8">
              <section>
                <label className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-3 block">
                  Step 1: Select Schema
                </label>
                <ThemedSelect
                  accent="blue"
                  value={selectedSchema}
                  options={schemas}
                  onChange={(v) => {
                    setSelectedSchema(v)
                    setSelectedTables([])
                  }}
                  placeholder="Choose a Schema..."
                  icon={<Database className="h-3.5 w-3.5" />}
                />

              </section>

              <section>
                <label className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-3 block">
                  Step 2: Find Tables
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input
                    placeholder="Table name filter..."
                    className="w-full pl-10 pr-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    disabled={!selectedSchema}
                  />
                </div>
              </section>

              <section className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-2xl border border-blue-100 dark:border-blue-900/20">
                <h3 className="text-sm font-bold text-blue-900 dark:text-blue-100 mb-2 flex items-center gap-2">
                  <Table size={16} /> Selection Summary
                </h3>
                <div className="flex justify-between items-center text-sm mb-4">
                  <span className="text-blue-700 dark:text-blue-300">Selected Tables:</span>
                  <span className="font-mono font-bold text-blue-900 dark:text-blue-100 bg-blue-200 dark:bg-blue-800 px-2 py-0.5 rounded-full">
                    {selectedTables.length}
                  </span>
                </div>
                <button
                  id="start-migration-master"
                  disabled={selectedTables.length === 0}
                  onClick={handleSave}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-3 rounded-xl shadow-lg shadow-blue-500/30 flex items-center justify-center gap-2 transition-all active:scale-95"
                >
                  Start Migration <Play size={16} fill="currentColor" />
                </button>
              </section>
            </div>

            {/* RIGHT COLUMN: Table List */}
            <div className="lg:col-span-2">
              {!selectedSchema ? (
                <div className="h-full min-h-[400px] flex flex-col items-center justify-center border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-3xl p-10 text-center bg-gray-50/30 dark:bg-gray-800/5">
                  {isLoading ? (
                    <div className="animate-in fade-in zoom-in duration-500">
                      <div className="w-16 h-16 border-4 border-blue-500/10 border-t-blue-600 rounded-full animate-spin mb-6 mx-auto" />
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white uppercase tracking-widest">
                        Syncing Metadata
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 max-w-xs">
                        Wait a moment while we fetch the latest schema information from your source database.
                      </p>
                    </div>
                  ) : (
                    <div className="animate-in fade-in zoom-in duration-500">
                      <Database size={48} className="text-blue-500/50 dark:text-blue-400/30 mb-6 mx-auto" />
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white uppercase">
                        {tables.length > 0 ? "Ready for Selection" : "Metadata Synchronized"}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-3 max-w-xs mx-auto">
                        {tables.length > 0
                          ? "Great! Use the sidebar on the left to filter by schema and select the tables you want to migrate."
                          : "Your connection is active. Please select a schema to begin mapping your data flow."}
                      </p>

                      {tables.length > 0 && (
                        <div className="mt-8 flex items-center gap-2 text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/10 px-4 py-2 rounded-full border border-emerald-100 dark:border-emerald-800/30">
                          <Check size={14} /> Metadata Fetched Successfully
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col h-full">
                  <div className="flex items-center justify-between mb-4 px-1">
                    <span className="text-sm font-medium text-gray-500">
                      Showing <b>{filteredTables.length}</b> of {schemaTablesCount} tables
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setSelectedTables(filteredTables.map(t => t.table))}
                        className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        Select All
                      </button>
                      <span className="text-gray-300 dark:text-gray-700">|</span>
                      <button
                        onClick={() => setSelectedTables([])}
                        className="text-xs font-bold text-red-600 dark:text-red-400 hover:underline"
                      >
                        Clear All
                      </button>
                    </div>
                  </div>

                  <div className="h-[550px] grid grid-cols-1 sm:grid-cols-2 gap-3 content-start overflow-y-auto pr-2 custom-scrollbar border-t border-gray-100 dark:border-gray-800 pt-4">
                    {isLoading ? (
                      <div className="col-span-full flex flex-col items-center justify-center py-20">
                        <div className="w-10 h-10 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-4" />
                        <p className="text-gray-500 font-medium animate-pulse">Syncing metadata...</p>
                      </div>
                    ) : (
                      filteredTables.map((t) => (
                        <label
                          key={t.table}
                          className={`flex items-center gap-3 p-4 rounded-2xl border transition-all cursor-pointer select-none
                        ${selectedTables.includes(t.table)
                              ? "bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800 shadow-sm"
                              : "bg-gray-50/50 dark:bg-gray-800/50 border-gray-100 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-600"
                            }`}
                        >
                          <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-all
                        ${selectedTables.includes(t.table)
                              ? "bg-blue-600 border-blue-600 text-white"
                              : "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600"
                            }`}>
                            {selectedTables.includes(t.table) && <Check size={14} strokeWidth={4} />}
                          </div>
                          <input
                            type="checkbox"
                            className="hidden"
                            checked={selectedTables.includes(t.table)}
                            onChange={() => toggleTable(t.table)}
                          />
                          <div className="flex flex-col">
                            <span
                              title={t.table}
                              className={`font-bold text-sm ${selectedTables.includes(t.table) ? "text-blue-700 dark:text-blue-300" : "text-gray-700 dark:text-gray-300"} line-clamp-1 break-all`}
                            >
                              {t.table}
                            </span>
                            {t.primaryKey && (
                              <span className="text-[10px] text-gray-400 dark:text-gray-500 font-mono mt-0.5">PK: {t.primaryKey}</span>
                            )}
                          </div>
                        </label>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}

export default SourceMapper