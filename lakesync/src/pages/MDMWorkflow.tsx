import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  ChevronLeftIcon,
  ShieldCheckIcon,
  TableCellsIcon,
  ArrowsRightLeftIcon,
  PlayIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  PlusIcon,
  TrashIcon,
  ArrowUpTrayIcon,
  CircleStackIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline';

import devConfig from '../data/dev_config.json';

const API_BASE = "https://lakesync-gateway.onrender.com";

interface MDMWorkflowProps {
  onBack: () => void;
  onBackToPipeline?: () => void;
}

interface ColumnMapItem {
  src: string;
  tgt: string;
  match_weight: number | null;
  normalize: 'text' | 'email' | 'phone' | 'none';
}

interface SelectedTable {
  database: string;
  schema: string;
  table: string;
  source_system: string;
  stream_name?: string;        // from CSV STREAM_NAME column
  // Filled in from CSV TGT_TABLE or after replication
  bronze_table?: string;
  bronze_schema?: string;
  bronze_database?: string;
}

// Simple CSV parser supporting quotes and escaped quotes
const parseCSV = (text: string) => {
  const lines = [];
  let row = [];
  let inQuotes = false;
  let cell = '';

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (inQuotes) {
      if (char === '"') {
        if (nextChar === '"') {
          cell += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cell += char;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
      } else if (char === ',') {
        row.push(cell);
        cell = '';
      } else if (char === '\n' || char === '\r') {
        row.push(cell);
        if (row.some(c => c !== '')) {
          lines.push(row);
        }
        row = [];
        cell = '';
        if (char === '\r' && nextChar === '\n') {
          i++;
        }
      } else {
        cell += char;
      }
    }
  }
  if (cell !== '' || row.length > 0) {
    row.push(cell);
    lines.push(row);
  }
  return lines;
};

export const MDMWorkflow: React.FC<MDMWorkflowProps> = ({ onBack, onBackToPipeline }) => {
  const [currentStep, setCurrentStep] = useState<number>(() => {
    try {
      const stored = localStorage.getItem('lake_sync_mdm_step');
      if (stored) {
        const parsed = parseInt(stored, 10);
        if (parsed >= 1 && parsed <= 4) return parsed;
      }
    } catch (e) { /* ignore */ }
    return 1;
  });

  useEffect(() => {
    localStorage.setItem('lake_sync_mdm_step', String(currentStep));
  }, [currentStep]);

  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Ref to prevent auto-init from overwriting CSV-uploaded mappings.
  // When set, holds the list of tgt column names extracted from the CSV so the
  // useEffect can populate the dropdown without relying on async state.
  const csvTgtColsRef = useRef<string[] | null>(null);

  // Step 1: Snowflake Credentials (No Database/Schema inputs)
  const [creds, setCreds] = useState<Record<string, string>>(() => {
    try {
      const stored = localStorage.getItem('lake_sync_abap_snowflake');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.account && parsed.username && parsed.password) {
          return parsed;
        }
      }
    } catch (e) { /* ignore */ }
    return {
      account: devConfig?.mdm?.account || '',
      username: devConfig?.mdm?.username || '',
      password: devConfig?.mdm?.password || '',
      warehouse: devConfig?.mdm?.warehouse || 'COMPUTE_WH',
    };
  });

  // Persist Snowflake credentials
  useEffect(() => {
    localStorage.setItem('lake_sync_abap_snowflake', JSON.stringify(creds));
  }, [creds]);

  // Auto-advance to Step 2 if credentials are already present in localStorage and we are on Step 1
  useEffect(() => {
    const hasCreds = creds.account && creds.username && creds.password && creds.warehouse;
    if (hasCreds && currentStep === 1) {
      setCurrentStep(2);
    }
  }, []);

  // ───────────────────────────── STEP 2 STATE ─────────────────────────────
  const [groupName, setGroupName] = useState<string>(() => {
    try {
      const stored = localStorage.getItem('lake_sync_mdm_group_name');
      if (stored) return stored;
    } catch (e) { /* ignore */ }
    return 'CUSTOMER_UNIFICATION';
  });

  useEffect(() => {
    localStorage.setItem('lake_sync_mdm_group_name', groupName);
  }, [groupName]);

  // The user builds a list of selected tables
  const [selectedTables, setSelectedTables] = useState<SelectedTable[]>(() => {
    try {
      const stored = localStorage.getItem('lake_sync_mdm_selected_tables');
      if (stored) return JSON.parse(stored);
    } catch (e) { /* ignore */ }
    return [];
  });

  useEffect(() => {
    localStorage.setItem('lake_sync_mdm_selected_tables', JSON.stringify(selectedTables));
  }, [selectedTables]);

  // Selector dropdowns: databases, schemas, tables - loaded from Snowflake
  const [databases, setDatabases] = useState<string[]>([]);
  const [schemas, setSchemas] = useState<string[]>([]);
  const [tablesInSchema, setTablesInSchema] = useState<string[]>([]);

  const [loadingDatabases, setLoadingDatabases] = useState(false);
  const [loadingSchemas, setLoadingSchemas] = useState(false);
  const [loadingTables, setLoadingTables] = useState(false);

  // Currently selected values in the picker form
  const [pickerDb, setPickerDb] = useState('');
  const [pickerSchema, setPickerSchema] = useState('');
  const [pickerTable, setPickerTable] = useState('');
  const [pickerSourceSystem, setPickerSourceSystem] = useState('');

  // Replication progress
  const [replicationResults] = useState<any[]>([]);
  const [isReplicating] = useState(false);

  // ───────────────────────────── STEP 3 STATE ─────────────────────────────
  const [stgColumns, setStgColumns] = useState<string[]>([]);
  const [tgtColumns, setTgtColumns] = useState<string[]>([]);
  const [mappingsByTable, setMappingsByTable] = useState<Record<string, ColumnMapItem[]>>(() => {
    try {
      const stored = localStorage.getItem('lake_sync_mdm_mappings');
      if (stored) return JSON.parse(stored);
    } catch (e) { /* ignore */ }
    return {};
  });

  useEffect(() => {
    localStorage.setItem('lake_sync_mdm_mappings', JSON.stringify(mappingsByTable));
  }, [mappingsByTable]);

  const [selectedTableKey, setSelectedTableKey] = useState<string>(() => {
    try {
      const stored = localStorage.getItem('lake_sync_mdm_selected_table_key');
      if (stored) return stored;
    } catch (e) { /* ignore */ }
    return '';
  });

  useEffect(() => {
    localStorage.setItem('lake_sync_mdm_selected_table_key', selectedTableKey);
  }, [selectedTableKey]);

  // ───────────────────────────── STEP 4 STATE ─────────────────────────────
  const [executionLogs, setExecutionLogs] = useState<any[]>([]);
  const [masterRecords, setMasterRecords] = useState<any[]>([]);

  // ─────────────────────── STEP 2: FETCH DATABASES ────────────────────────
  const fetchDatabases = useCallback(async () => {
    setLoadingDatabases(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${API_BASE}/mdm/databases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creds })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to fetch databases');
      setDatabases(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setErrorMessage(`Could not load databases: ${err.message}`);
    } finally {
      setLoadingDatabases(false);
    }
  }, [creds]);

  // Fetch databases when entering step 2
  useEffect(() => {
    if (currentStep === 2 && databases.length === 0) {
      fetchDatabases();
    }
  }, [currentStep]);

  const fetchSchemas = useCallback(async (db: string) => {
    if (!db) return;
    setLoadingSchemas(true);
    setSchemas([]);
    setPickerSchema('');
    setTablesInSchema([]);
    setPickerTable('');
    setErrorMessage(null);
    try {
      const res = await fetch(`${API_BASE}/mdm/schemas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creds, database: db })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to fetch schemas');
      setSchemas(Array.isArray(data) ? data.filter((s: string) => !['INFORMATION_SCHEMA'].includes(s)) : []);
    } catch (err: any) {
      setErrorMessage(`Could not load schemas: ${err.message}`);
    } finally {
      setLoadingSchemas(false);
    }
  }, [creds]);

  const fetchTablesInSchema = useCallback(async (db: string, schema: string) => {
    if (!db || !schema) return;
    setLoadingTables(true);
    setTablesInSchema([]);
    setPickerTable('');
    setErrorMessage(null);
    try {
      const res = await fetch(`${API_BASE}/mdm/tables`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creds: { ...creds, database: db, schema }, schema })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to fetch tables');
      setTablesInSchema(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setErrorMessage(`Could not load tables: ${err.message}`);
    } finally {
      setLoadingTables(false);
    }
  }, [creds]);

  const addTableToList = () => {
    if (!pickerDb || !pickerSchema || !pickerTable) {
      setErrorMessage('Please select a database, schema, and table before adding.');
      return;
    }
    const duplicate = selectedTables.find(
      t => t.database === pickerDb && t.schema === pickerSchema && t.table === pickerTable
    );
    if (duplicate) {
      setErrorMessage('This table is already in the list.');
      return;
    }
    setErrorMessage(null);
    const sys = (pickerSourceSystem ?? '').trim().toUpperCase() || (pickerDb ?? '').split('_')[0] || 'SOURCE';
    setSelectedTables(prev => [...prev, {
      database: pickerDb,
      schema: pickerSchema,
      table: pickerTable,
      source_system: sys
    }]);
    setPickerTable('');
    setPickerSourceSystem('');
  };

  const removeTable = (idx: number) => {
    const removed = selectedTables[idx];
    const key = `${removed.database}:${removed.schema}:${removed.table}`;
    setSelectedTables(prev => prev.filter((_, i) => i !== idx));
    setMappingsByTable(prev => {
      const copy = { ...prev };
      delete copy[key];
      return copy;
    });
  };

  const proceedToMap = () => {
    if (selectedTables.length === 0) {
      setErrorMessage('Please add at least one table before proceeding.');
      return;
    }
    if (!groupName.trim()) {
      setErrorMessage('Please enter a group name.');
      return;
    }
    setErrorMessage(null);
    // Set the first table as the active mapping tab
    setSelectedTableKey(`${selectedTables[0].database}:${selectedTables[0].schema}:${selectedTables[0].table}`);
    setCurrentStep(3);
  };

  // ─────────────────────── STEP 3: LOAD COLUMNS ───────────────────────────
  useEffect(() => {
    if (!selectedTableKey) return;
    const currentTable = selectedTables.find(
      t => `${t.database}:${t.schema}:${t.table}` === selectedTableKey
    );
    if (!currentTable) return;

    const loadColumnsForSelectedTable = async () => {
      setIsProcessing(true);
      try {
        // Source table columns
        const stgRes = await fetch(`${API_BASE}/mdm/columns`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            creds: { ...creds, database: currentTable.database, schema: currentTable.schema },
            schema: currentTable.schema,
            table: currentTable.table
          })
        });

        // Bronze target table columns - only if replication info is available
        const bronzeDb = currentTable.bronze_database || currentTable.database;
        const bronzeSchema = currentTable.bronze_schema || 'BRONZE';
        const bronzeTable = currentTable.bronze_table || `BRONZE_${currentTable.table}`;

        const tgtRes = await fetch(`${API_BASE}/mdm/columns`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            creds: { ...creds, database: bronzeDb, schema: bronzeSchema },
            schema: bronzeSchema,
            table: bronzeTable
          })
        });

        const stgCols = stgRes.ok ? await stgRes.json() : [];
        const tgtCols = tgtRes.ok ? await tgtRes.json() : [];

        const stgColNames = (Array.isArray(stgCols) ? stgCols : []).map((c: any) => c?.column_name).filter(Boolean);
        const tgtColNames = (Array.isArray(tgtCols) ? tgtCols : []).map((c: any) => c?.column_name)
          .filter((c: string) => c && !['SOURCE_SYSTEM', 'LOAD_TIMESTAMP', 'LAST_MODIFIED_DATE'].includes(c));

        setStgColumns(stgColNames);

        // Always merge any existing mapping tgt values into the dropdown.
        // This covers two cases:
        //   1. CSV just uploaded (csvTgtColsRef has the tgt list)
        //   2. Switching between source tabs (mappingsByTable already has tgt values)
        // Either way the dropdown must contain all tgt values referenced in the mappings.
        const reserved = new Set(['SOURCE_SYSTEM', 'LOAD_TIMESTAMP', 'LAST_MODIFIED_DATE']);

        let extraTgtCols: string[] = [];
        if (csvTgtColsRef.current !== null) {
          // Fresh CSV upload: use the pre-extracted list from the ref
          extraTgtCols = csvTgtColsRef.current;
          csvTgtColsRef.current = null; // consume
        } else {
          // Switching tabs: derive from existing state mappings for this table
          // NOTE: mappingsByTable is NOT in the dep array so we read it from
          // the closure; it may be slightly stale but will already have CSV values.
          const existingMappings = mappingsByTable[selectedTableKey] || [];
          extraTgtCols = (Array.isArray(existingMappings) ? existingMappings : [])
            .map((m: ColumnMapItem) => m?.tgt)
            .filter((t: string) => t && !reserved.has(t));
        }

        // Union: API-returned tgt cols + extra tgt cols, deduped
        const merged = Array.from(new Set([...(tgtColNames || []), ...(extraTgtCols || [])]));
        setTgtColumns(merged);

        // Auto-init only when no mappings exist yet for this table
        if (extraTgtCols.length > 0) {
          // Mappings already exist (CSV or prior auto-init) — skip
          return;
        }

        if (!mappingsByTable[selectedTableKey] || mappingsByTable[selectedTableKey].length === 0) {
          const initialMappings = tgtColNames.map((tCol: string) => {
            const tColUpper = (tCol ?? '').toUpperCase();
            // Try exact name match
            let matchingSrc = stgColNames.find((s: string) => (s ?? '').toUpperCase() === tColUpper);
            // If not found, try normalized match
            if (!matchingSrc) {
              matchingSrc = stgColNames.find((s: string) => {
                const sUpper = (s ?? '').toUpperCase();
                const tUpper = tColUpper;
                return sUpper.includes(tUpper) || tUpper.includes(sUpper);
              });
            }

            let weight: number | null = null;
            let norm: 'none' | 'text' | 'email' | 'phone' = 'none';
            const nameLower = (tCol ?? '').toLowerCase();

            if (nameLower === 'name' || nameLower.includes('name')) {
              weight = 0.15; norm = 'text';
            } else if (nameLower === 'email' || nameLower.includes('email') || nameLower.includes('smtp')) {
              weight = 0.40; norm = 'email';
            } else if (nameLower === 'phone' || nameLower.includes('phone') || nameLower.includes('telf') || nameLower.includes('mobile')) {
              weight = 0.30; norm = 'phone';
            } else if (nameLower === 'city' || nameLower.includes('city')) {
              weight = 0.15; norm = 'text';
            } else if (nameLower.includes('state')) {
              norm = 'text';
            } else if (nameLower.includes('country')) {
              norm = 'text';
            }

            return {
              src: matchingSrc || '',
              tgt: tCol,
              match_weight: weight,
              normalize: norm
            };
          });

          setMappingsByTable(prev => ({
            ...prev,
            [selectedTableKey]: initialMappings
          }));
        }
      } catch (err) {
        console.error('Failed to load columns for table:', err);
      } finally {
        setIsProcessing(false);
      }
    };

    loadColumnsForSelectedTable();
  }, [selectedTableKey, selectedTables]);

  const handleCredsChange = (key: string, val: string) => {
    setCreds(prev => ({ ...prev, [key]: val }));
  };

  const verifyCredentials = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${API_BASE}/mdm/test-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(creds)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Connection failed');

      setSuccessMessage('Successfully connected to Snowflake!');
      setTimeout(() => setSuccessMessage(null), 3000);
      setCurrentStep(2);
    } catch (e: any) {
      setErrorMessage(e.message || 'Failed to verify connection');
    } finally {
      setIsProcessing(false);
    }
  };

  // ─────────────────────── STEP 2+3: CSV UPLOAD (shared handler) ──────────
  // handleCSVUpload is used in both Step 2 (primary) and Step 3 (optional re-upload).
  // It parses the mapping file, sets selectedTables (with bronze_table names from TGT_TABLE
  // and stream_name from STREAM_NAME column), populates mappingsByTable, and sets groupName.
  const handleCSVUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        if (!text) return;

        const rows = parseCSV(text);
        if (rows.length < 2) {
          setErrorMessage('The CSV file is empty or invalid.');
          return;
        }

        const headers = rows[0].map(h => h.toUpperCase().trim());

        const groupNameIdx = headers.indexOf('GROUP_NAME');
        const sourceSystemIdx = headers.indexOf('SOURCE_SYSTEM');
        const srcDbIdx = headers.indexOf('SRC_DATABASE');
        const stgSchemaIdx = headers.indexOf('STG_SCHEMA');
        const stgTableIdx = headers.indexOf('STG_TABLE');
        const tgtDbIdx = headers.indexOf('TGT_DATABASE');
        const tgtSchemaIdx = headers.indexOf('TGT_SCHEMA');
        const tgtTableIdx = headers.indexOf('TGT_TABLE');
        const streamNameIdx = headers.indexOf('STREAM_NAME');
        const columnMappingIdx = headers.indexOf('COLUMN_MAPPING');

        if (sourceSystemIdx === -1 || stgTableIdx === -1 || tgtTableIdx === -1 || columnMappingIdx === -1) {
          setErrorMessage('CSV is missing required headers: SOURCE_SYSTEM, STG_TABLE, TGT_TABLE, COLUMN_MAPPING.');
          return;
        }

        const newTables: SelectedTable[] = [];
        const newMappings: Record<string, ColumnMapItem[]> = {};

        for (let i = 1; i < rows.length; i++) {
          const row = rows[i];
          if (row.length < headers.length) continue;

          let rowGroupName = groupNameIdx !== -1 ? row[groupNameIdx] : '';
          if (!rowGroupName || rowGroupName.trim() !== groupName.trim()) {
            rowGroupName = groupName;
          }

          const sourceSystem = row[sourceSystemIdx];
          const stgTable = row[stgTableIdx];
          const tgtTable = row[tgtTableIdx];
          const srcDb = srcDbIdx !== -1 ? row[srcDbIdx] : '';
          const stgSchema = stgSchemaIdx !== -1 ? row[stgSchemaIdx] : '';
          const tgtDb = tgtDbIdx !== -1 ? row[tgtDbIdx] : '';
          const tgtSchema = tgtSchemaIdx !== -1 ? row[tgtSchemaIdx] : 'BRONZE';

          const tableKey = `${srcDb}:${stgSchema}:${stgTable}`;

          newTables.push({
            source_system: sourceSystem,
            database: srcDb,
            schema: stgSchema,
            table: stgTable,
            // TGT_TABLE becomes the bronze table name (e.g. SAP_CUSTOMER_MASTER)
            bronze_table: tgtTable,
            bronze_schema: tgtSchema,
            bronze_database: tgtDb || srcDb,
            // STREAM_NAME from CSV (e.g. STM_SAP_CUSTOMER_MASTER)
            stream_name: streamNameIdx !== -1 ? row[streamNameIdx] : `STM_${tgtTable}`
          });

          let mappingArray: ColumnMapItem[] = [];
          try {
            const jsonStr = row[columnMappingIdx];
            if (jsonStr) {
              const parsed: ColumnMapItem[] = JSON.parse(jsonStr);
              // Filter out const: entries — these set SOURCE_SYSTEM to a constant
              // value (e.g. const:SAP) and are handled automatically by SP_LOAD_GROUP.
              // Showing them in the UI mapping table would be confusing since
              // SOURCE_SYSTEM is excluded from the target column dropdown.
              mappingArray = parsed.filter(
                (m: ColumnMapItem) => !String(m.src).startsWith('const:')
              );
            }
          } catch (jsonErr) {
            console.error(`Failed to parse COLUMN_MAPPING for row ${i}:`, jsonErr);
          }
          newMappings[tableKey] = mappingArray;
        }

        setSelectedTables(newTables);
        setMappingsByTable(newMappings);

        if (newTables.length > 0) {
          const firstKey = `${newTables[0].database}:${newTables[0].schema}:${newTables[0].table}`;

          // Collect all unique tgt column names from all CSV mappings (excluding reserved cols).
          // Store in a ref so the useEffect reads them synchronously without relying on async state.
          const reserved = new Set(['SOURCE_SYSTEM', 'LOAD_TIMESTAMP', 'LAST_MODIFIED_DATE']);
          const allTgtCols: string[] = [];
          for (const mappings of Object.values(newMappings)) {
            for (const m of mappings) {
              if (m.tgt && !reserved.has(m.tgt) && !allTgtCols.includes(m.tgt)) {
                allTgtCols.push(m.tgt);
              }
            }
          }
          csvTgtColsRef.current = allTgtCols;

          setSelectedTableKey(firstKey);
        }

        setSuccessMessage('CSV mapping file uploaded and validated successfully!');
        setTimeout(() => setSuccessMessage(null), 3000);
      } catch (err: any) {
        setErrorMessage('Error reading or parsing CSV file: ' + err.message);
      }
    };
    reader.readAsText(file);
  };

  // ─────────────────────── STEP 3: MAPPING ACTIONS ────────────────────────
  const addMappingRow = () => {
    if (!selectedTableKey) return;
    setMappingsByTable(prev => {
      const current = prev[selectedTableKey] || [];
      return {
        ...prev,
        [selectedTableKey]: [...current, { src: '', tgt: '', match_weight: null, normalize: 'none' }]
      };
    });
  };

  const removeMappingRow = (idx: number) => {
    if (!selectedTableKey) return;
    setMappingsByTable(prev => {
      const current = prev[selectedTableKey] || [];
      return {
        ...prev,
        [selectedTableKey]: current.filter((_, i) => i !== idx)
      };
    });
  };

  const updateMappingRow = (idx: number, key: keyof ColumnMapItem, val: any) => {
    if (!selectedTableKey) return;
    setMappingsByTable(prev => {
      const current = prev[selectedTableKey] || [];
      const updated = current.map((m, i) => i === idx ? { ...m, [key]: val } : m);
      return { ...prev, [selectedTableKey]: updated };
    });
  };

  // ─────────────────────── STEP 3: CONFIGURE & PROCEED ────────────────────
  // "Save Mapping & Run" does three things in sequence:
  //   1. Create / replace Bronze tables using the column mappings from the CSV
  //   2. Configure MDM (save SOURCE_MAPPING_CONFIG, create streams, deploy SPs)
  //   3. Advance to Step 4
  const configureMDM = async () => {
    if (selectedTables.length === 0) {
      setErrorMessage('No tables configured.');
      return;
    }
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      // ── Phase 1: Create Bronze tables with the correct names & column structure ──
      const bronzePayloadTables = selectedTables.map(t => {
        const key = `${t.database}:${t.schema}:${t.table}`;
        const mappings = (mappingsByTable[key] || []).filter(
          m => m.src.trim() !== '' && m.tgt.trim() !== ''
        );
        return {
          database: t.database,
          schema: t.schema,
          table: t.table,
          source_system: t.source_system,
          bronze_table: t.bronze_table || `BRONZE_${t.table}`,
          bronze_schema: t.bronze_schema || 'BRONZE',
          bronze_database: t.bronze_database || t.database,
          column_mapping: mappings
        };
      });

      const bronzeRes = await fetch(`${API_BASE}/mdm/replicate-to-bronze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          creds,
          group_name: groupName,
          tables: bronzePayloadTables
        })
      });
      const bronzeData = await bronzeRes.json();
      if (!bronzeRes.ok) throw new Error(bronzeData.detail || 'Failed to create Bronze tables');

      // Update selectedTables with confirmed bronze info from the replicate response
      const resultMap: Record<string, any> = {};
      for (const r of (bronzeData.results || [])) {
        const key = `${r.database}:${r.schema}:${r.table}`;
        resultMap[key] = r;
      }
      setSelectedTables(prev => prev.map(t => {
        const key = `${t.database}:${t.schema}:${t.table}`;
        const r = resultMap[key];
        if (r && r.status === 'SUCCESS') {
          return { ...t, bronze_table: r.bronze_table, bronze_schema: r.bronze_schema, bronze_database: r.bronze_database };
        }
        return t;
      }));

      // ── Phase 2: Configure MDM (SOURCE_MAPPING_CONFIG + streams + procedures) in a single Batch call ──
      const batchConfigs = selectedTables.map(tableConfig => {
        const tableKey = `${tableConfig.database}:${tableConfig.schema}:${tableConfig.table}`;
        const tableMappings = mappingsByTable[tableKey] || [];
        const cleanMappings = tableMappings.filter(
          m => m.src.trim() !== '' && m.tgt.trim() !== '' && !m.src.startsWith('const:')
        );

        const rInfo = resultMap[tableKey];
        const bronzeSchema = rInfo?.bronze_schema   || tableConfig.bronze_schema   || 'BRONZE';
        const bronzeTable  = rInfo?.bronze_table    || tableConfig.bronze_table    || `BRONZE_${tableConfig.table}`;

        return {
          source_system: tableConfig.source_system,
          src_db: tableConfig.database,
          stg_schema: tableConfig.schema,
          stg_table: tableConfig.table,
          tgt_schema: bronzeSchema,
          tgt_table: bronzeTable,
          merge_key: cleanMappings.find(m => !m.match_weight)?.tgt || cleanMappings[0]?.tgt || 'CUSTOMER_ID',
          stg_merge_key: cleanMappings.find(m => !m.match_weight)?.src || cleanMappings[0]?.src || '',
          column_mapping: cleanMappings.map(m => ({
            src: m.src,
            tgt: m.tgt,
            match_weight: m.match_weight ? parseFloat(m.match_weight as any) : null,
            normalize: m.normalize
          })),
          stream_name: tableConfig.stream_name || `STM_${bronzeTable}`
        };
      });

      // Use the database and schema from the first selected table's confirmed bronze info
      const firstTableKey = `${selectedTables[0].database}:${selectedTables[0].schema}:${selectedTables[0].table}`;
      const firstTableRInfo = resultMap[firstTableKey];
      const batchBronzeDb = firstTableRInfo?.bronze_database || selectedTables[0].bronze_database || selectedTables[0].database;
      const batchBronzeSchema = firstTableRInfo?.bronze_schema || selectedTables[0].bronze_schema || 'BRONZE';

      const batchPayload = {
        creds: { ...creds, database: batchBronzeDb, schema: batchBronzeSchema },
        group_name: groupName,
        configs: batchConfigs
      };

      const res = await fetch(`${API_BASE}/mdm/configure/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batchPayload)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to deploy batch MDM configurations');
      }

      setSuccessMessage('Bronze tables created & MDM configurations deployed successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
      fetchStatus();
      setCurrentStep(4);
    } catch (e: any) {
      setErrorMessage(e.message || 'Error deploying configuration');
    } finally {
      setIsProcessing(false);
    }
  };

  // ─────────────────────── STEP 4: EXECUTION ──────────────────────────────
  const runUnification = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const bronzeDb = selectedTables[0]?.bronze_database || selectedTables[0]?.database || '';
      const res = await fetch(`${API_BASE}/mdm/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          creds: { ...creds, database: bronzeDb },
          group_name: groupName
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Execution failed');

      setSuccessMessage('MDM Unification executed successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
      fetchStatus();
    } catch (e: any) {
      setErrorMessage(e.message || 'Error executing MDM pipeline');
    } finally {
      setIsProcessing(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const bronzeDb = selectedTables[0]?.bronze_database || selectedTables[0]?.database || '';
      const res = await fetch(`${API_BASE}/mdm/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          creds: { ...creds, database: bronzeDb },
          group_name: groupName
        })
      });
      if (res.ok) {
        const data = await res.json();
        setExecutionLogs(data.logs || []);
        setMasterRecords(data.records || []);
      }
    } catch (e) {
      console.error('Failed to fetch MDM status', e);
    }
  };

  const steps = [
    { id: 1, label: 'Credentials', icon: ShieldCheckIcon },
    { id: 2, label: 'Tables', icon: TableCellsIcon },
    { id: 3, label: 'Mapping', icon: ArrowsRightLeftIcon },
    { id: 4, label: 'Execution', icon: PlayIcon }
  ];

  const currentMappings = selectedTableKey ? (mappingsByTable[selectedTableKey] || []) : [];

  return (
    <div className="container mx-auto px-6 py-8 animate-fadeIn max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8 pb-5 border-b border-slate-200/60">
        <div className="text-left">
          <h2 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
            Snowflake MDM Unification
          </h2>
          <p className="text-sm text-slate-500 mt-1 font-medium">
            Match, merge, and de-duplicate records directly within Snowflake using Snowpark.
          </p>
        </div>

        {/* Wizard Progress — each completed step is clickable */}
        <div className="flex items-center gap-4">
          {steps.map((s) => {
            const Icon = s.icon;
            const active = currentStep === s.id;
            const completed = currentStep > s.id;
            const clickable = completed; // only go back, not forward
            return (
              <div key={s.id} className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (s.id === 1) {
                      if (onBackToPipeline) {
                        onBackToPipeline();
                      } else {
                        setCurrentStep(1);
                      }
                    } else if (clickable) {
                      setCurrentStep(s.id);
                    }
                  }}
                  disabled={!clickable && !active}
                  title={clickable ? `Go back to ${s.label}` : s.label}
                  className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all focus:outline-none
                    ${active ? 'bg-violet-600 text-white shadow-md shadow-violet-200 cursor-default' :
                    completed ? 'bg-emerald-500 text-white cursor-pointer hover:bg-emerald-600 hover:scale-110 shadow-sm shadow-emerald-100' :
                    'bg-slate-100 text-slate-400 cursor-default'}`}
                >
                  {completed ? <CheckCircleIcon className="w-5 h-5" /> : <Icon className="w-4.5 h-4.5" />}
                </button>
                <span
                  onClick={() => {
                    if (s.id === 1) {
                      if (onBackToPipeline) {
                        onBackToPipeline();
                      } else {
                        setCurrentStep(1);
                      }
                    } else if (clickable) {
                      setCurrentStep(s.id);
                    }
                  }}
                  className={`text-xs font-bold hidden md:inline transition-colors
                    ${active ? 'text-violet-700' :
                    completed ? 'text-emerald-600 cursor-pointer hover:text-emerald-700 hover:underline' :
                    'text-slate-400'}`}
                >
                  {s.label}
                </span>
                {s.id < 4 && <span className="text-slate-300 mx-1">/</span>}
              </div>
            );
          })}
        </div>

        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-450 hover:text-slate-700 font-bold transition-colors">
          <ChevronLeftIcon className="w-4 h-4 stroke-[2.5]" /> Dashboard
        </button>
      </div>

      {/* Messages */}
      {errorMessage && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-start gap-3 text-rose-800 text-sm font-medium animate-fadeIn text-left">
          <ExclamationTriangleIcon className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold text-rose-900 block mb-0.5">Operation Error</span>
            <span className="text-xs text-rose-700 leading-relaxed font-semibold">{errorMessage}</span>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="mb-6 p-4 bg-emerald-50 border border-emerald-100 rounded-2xl flex items-start gap-3 text-emerald-800 text-sm font-medium animate-fadeIn text-left">
          <CheckCircleIcon className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold text-emerald-900 block mb-0.5">Success</span>
            <span className="text-xs text-emerald-700 leading-relaxed font-semibold">{successMessage}</span>
          </div>
        </div>
      )}

      {/* ═══════════════════ STEP 1: CREDENTIALS ═══════════════════ */}
      {currentStep === 1 && (
        <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm max-w-2xl mx-auto text-left animate-fadeIn">
          <h3 className="text-base font-bold text-slate-800 mb-2">Configure Snowflake Connection</h3>
          <p className="text-xs text-slate-400 font-medium mb-6">Enter your Snowflake credentials to connect and run MDM unification.</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Account URL</label>
              <input
                type="text"
                placeholder="e.g. xy12345.east-us-2.azure"
                value={creds.account}
                onChange={e => handleCredsChange('account', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Username</label>
              <input
                type="text"
                placeholder="Snowflake Username"
                value={creds.username}
                onChange={e => handleCredsChange('username', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Password</label>
              <input
                type="password"
                placeholder="Snowflake Password"
                value={creds.password}
                onChange={e => handleCredsChange('password', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Warehouse</label>
              <input
                type="text"
                placeholder="e.g. COMPUTE_WH"
                value={creds.warehouse}
                onChange={e => handleCredsChange('warehouse', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
            <button
              onClick={verifyCredentials}
              disabled={!creds.account || !creds.username || !creds.password || !creds.warehouse || isProcessing}
              className="flex items-center gap-2 px-6 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-bold text-xs disabled:bg-slate-300 disabled:cursor-not-allowed transition-all active:scale-95 shadow-md shadow-violet-100"
            >
              {isProcessing ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <SparklesIcon className="w-4 h-4" />}
              Connect &amp; Setup MDM
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════════ STEP 2: TABLE SELECTION ═══════════════════ */}
      {currentStep === 2 && (
        <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm max-w-6xl mx-auto text-left animate-fadeIn space-y-6">

          {/* Header row with group name */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-800">Select Unification Group &amp; Tables</h3>
              <p className="text-xs text-slate-400 font-medium mt-0.5">
                Give your unification group a name, then select the source tables to unify.
                You will upload the mapping file in the next step.
              </p>
            </div>
            <div className="w-72 shrink-0">
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Unification Group Name</label>
              <input
                type="text"
                value={groupName}
                onChange={e => setGroupName(e.target.value.toUpperCase())}
                placeholder="e.g. CUSTOMER_UNIFICATION"
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all font-bold"
              />
            </div>
          </div>


          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* ─── LEFT: Table Picker Form ─── */}
            <div className="lg:col-span-2 bg-slate-50/70 border border-slate-150 rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-black text-slate-700 uppercase tracking-wider">Add Table</h4>
                <button
                  onClick={fetchDatabases}
                  className="text-[9px] font-bold text-violet-600 hover:text-violet-700 underline flex items-center gap-1"
                >
                  {loadingDatabases ? <ArrowPathIcon className="w-3 h-3 animate-spin" /> : <ArrowPathIcon className="w-3 h-3" />}
                  Refresh Databases
                </button>
              </div>

              {/* Source System */}
              <div>
                <label className="block text-[9px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">Source System Label</label>
                <input
                  type="text"
                  placeholder="e.g. SAP, ORACLE, SALESFORCE"
                  value={pickerSourceSystem}
                  onChange={e => setPickerSourceSystem(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
                />
              </div>

              {/* Database */}
              <div>
                <label className="block text-[9px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                  Database {loadingDatabases && <span className="text-violet-500">(loading...)</span>}
                </label>
                <div className="relative">
                  <select
                    value={pickerDb}
                    onChange={e => {
                      setPickerDb(e.target.value);
                      if (e.target.value) fetchSchemas(e.target.value);
                    }}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all appearance-none pr-8"
                  >
                    <option value="">— Select Database —</option>
                    {databases.map(db => <option key={db} value={db}>{db}</option>)}
                  </select>
                  <CircleStackIcon className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                </div>
              </div>

              {/* Schema */}
              <div>
                <label className="block text-[9px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                  Schema {loadingSchemas && <span className="text-violet-500">(loading...)</span>}
                </label>
                <div className="relative">
                  <select
                    value={pickerSchema}
                    onChange={e => {
                      setPickerSchema(e.target.value);
                      if (e.target.value) fetchTablesInSchema(pickerDb, e.target.value);
                    }}
                    disabled={!pickerDb || loadingSchemas}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all appearance-none pr-8 disabled:bg-slate-100 disabled:text-slate-400"
                  >
                    <option value="">— Select Schema —</option>
                    {schemas.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <ChevronDownIcon className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                </div>
              </div>

              {/* Table */}
              <div>
                <label className="block text-[9px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                  Table {loadingTables && <span className="text-violet-500">(loading...)</span>}
                </label>
                <div className="relative">
                  <select
                    value={pickerTable}
                    onChange={e => setPickerTable(e.target.value)}
                    disabled={!pickerSchema || loadingTables}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all appearance-none pr-8 disabled:bg-slate-100 disabled:text-slate-400"
                  >
                    <option value="">— Select Table —</option>
                    {tablesInSchema.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                  <TableCellsIcon className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                </div>
              </div>

              <button
                type="button"
                onClick={addTableToList}
                disabled={!pickerDb || !pickerSchema || !pickerTable}
                className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-bold transition-all active:scale-95 shadow-sm mt-2 disabled:bg-slate-300 disabled:cursor-not-allowed"
              >
                <PlusIcon className="w-4 h-4 stroke-[2.5]" /> Add Table to Group
              </button>

              {/* Info box */}
              <div className="mt-3 p-3 bg-violet-50 border border-violet-100 rounded-xl">
                <p className="text-[9px] font-semibold text-violet-700 leading-relaxed">
                  <span className="font-black">How it works:</span> When you click <span className="font-black">"Proceed to Map"</span>, all selected tables will be automatically replicated to a <span className="font-black">BRONZE</span> schema in each source database with a unified column structure, plus <span className="font-mono font-bold">SOURCE_SYSTEM</span>, <span className="font-mono font-bold">LOAD_TIMESTAMP</span>, and <span className="font-mono font-bold">LAST_MODIFIED_DATE</span> columns.
                </p>
              </div>
            </div>

            {/* ─── RIGHT: Selected Tables List ─── */}
            <div className="lg:col-span-3 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-black text-slate-700 uppercase tracking-wider">
                  Selected Tables ({selectedTables.length})
                </h4>
                {selectedTables.length > 0 && (
                  <span className="text-[9px] text-violet-600 font-bold bg-violet-50 border border-violet-100 px-2 py-0.5 rounded-full">
                    Will be replicated to BRONZE on proceed
                  </span>
                )}
              </div>

              <div className="border border-slate-200 rounded-2xl overflow-hidden bg-white shadow-sm flex-1 min-h-[300px]">
                {selectedTables.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-150">
                      <thead className="bg-slate-50 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                        <tr>
                          <th className="px-4 py-3 text-left">Source System</th>
                          <th className="px-4 py-3 text-left">Database</th>
                          <th className="px-4 py-3 text-left">Schema</th>
                          <th className="px-4 py-3 text-left">Table</th>
                          <th className="px-4 py-3 text-left">Bronze Target</th>
                          <th className="relative px-4 py-3"><span className="sr-only">Remove</span></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-xs font-semibold text-slate-700 bg-white">
                        {selectedTables.map((t, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/50">
                            <td className="px-4 py-3">
                              <span className="px-2 py-0.5 rounded-md bg-violet-50 text-violet-700 font-bold border border-violet-100">{t.source_system}</span>
                            </td>
                            <td className="px-4 py-3 font-mono text-slate-600 text-[11px]">{t.database}</td>
                            <td className="px-4 py-3 font-mono text-slate-500 text-[11px]">{t.schema}</td>
                            <td className="px-4 py-3 font-bold text-slate-900">{t.table}</td>
                            <td className="px-4 py-3">
                              {t.bronze_table ? (
                                <span className="text-emerald-600 font-mono text-[10px] font-bold">
                                  {t.bronze_database}.BRONZE.{t.bronze_table}
                                </span>
                              ) : (
                                <span className="text-slate-400 text-[10px] font-medium italic">pending replication</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <button onClick={() => removeTable(idx)} className="text-slate-400 hover:text-rose-600 transition-colors">
                                <TrashIcon className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-72 text-slate-400 italic">
                    <TableCellsIcon className="w-12 h-12 text-slate-300 stroke-[1.5] mb-2 animate-pulse" />
                    <p className="text-xs font-semibold">No tables added yet.</p>
                    <p className="text-[10px] text-slate-400 mt-1 max-w-xs text-center font-medium">
                      Use the picker on the left to select a database, schema, and table to add.
                    </p>
                  </div>
                )}
              </div>

              {/* Replication progress */}
              {isReplicating && (
                <div className="mt-4 p-4 bg-violet-50 border border-violet-100 rounded-2xl animate-pulse">
                  <div className="flex items-center gap-2 text-violet-700">
                    <ArrowPathIcon className="w-4 h-4 animate-spin" />
                    <span className="text-xs font-bold">Replicating tables to BRONZE schema...</span>
                  </div>
                </div>
              )}

              {replicationResults.length > 0 && !isReplicating && (
                <div className="mt-4 space-y-2">
                  {replicationResults.map((r, idx) => (
                    <div key={idx} className={`flex items-center gap-2 px-3 py-2 rounded-xl text-[10px] font-semibold border ${r.status === 'SUCCESS' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 'bg-rose-50 border-rose-100 text-rose-700'
                      }`}>
                      {r.status === 'SUCCESS' ? (
                        <CheckCircleIcon className="w-3.5 h-3.5 shrink-0" />
                      ) : (
                        <ExclamationTriangleIcon className="w-3.5 h-3.5 shrink-0" />
                      )}
                      <span className="font-bold">{r.database}.{r.schema}.{r.table}</span>
                      <span className="text-slate-400 mx-1">→</span>
                      <span className="font-mono">{r.bronze_database}.BRONZE.{r.bronze_table}</span>
                      <span className="ml-auto">{r.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-between border-t border-slate-100 pt-4">
            <button
              onClick={() => {
                if (onBackToPipeline) {
                  onBackToPipeline();
                } else {
                  setCurrentStep(1);
                }
              }}
              className="px-5 py-2.5 border border-slate-200 hover:border-slate-350 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white transition-all active:scale-95"
            >
              Back
            </button>
            <button
              onClick={proceedToMap}
              disabled={selectedTables.length === 0 || isReplicating}
              className="flex items-center gap-2 px-6 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-bold text-xs transition-all active:scale-95 shadow-md shadow-violet-100 disabled:bg-slate-300 disabled:cursor-not-allowed"
            >
              {isReplicating ? (
                <><ArrowPathIcon className="w-4 h-4 animate-spin" /> Replicating to BRONZE...</>
              ) : (
                <>Proceed to Map</>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════════ STEP 3: COLUMN MAPPING & CSV UPLOAD ═══════════════════ */}
      {currentStep === 3 && (
        <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm text-left animate-fadeIn space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-800">Define Match Weight &amp; Normalization Rules</h3>
              <p className="text-xs text-slate-400 font-medium mt-0.5">Map source columns to unified BRONZE target columns. Upload a CSV file or configure manually.</p>
            </div>

            {/* CSV File Upload */}
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 px-4 py-2 border border-slate-200 hover:border-slate-350 rounded-xl text-xs font-bold text-slate-650 hover:text-slate-800 bg-white shadow-sm cursor-pointer transition-all active:scale-95">
                <ArrowUpTrayIcon className="w-4 h-4 text-slate-500" />
                Upload Mapping CSV
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleCSVUpload}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {/* Active Table Selector Tab Bar */}
          {selectedTables.length > 0 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mr-2 shrink-0">Configure Mapping For:</span>
              {selectedTables.map((t, idx) => {
                const key = `${t.database}:${t.schema}:${t.table}`;
                const active = selectedTableKey === key;
                return (
                  <button
                    key={idx}
                    onClick={() => setSelectedTableKey(key)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${active ? 'bg-violet-600 text-white border-violet-600 shadow-sm shadow-violet-100' : 'bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200'
                      }`}
                  >
                    {t.source_system} ({t.table})
                  </button>
                );
              })}
            </div>
          )}

          {/* Column Mapping Grid */}
          {selectedTableKey ? (
            <div className="space-y-4">
              {isProcessing && (
                <div className="flex items-center gap-2 text-violet-600 text-xs font-semibold">
                  <ArrowPathIcon className="w-4 h-4 animate-spin" /> Loading columns...
                </div>
              )}
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-800 flex items-center gap-2">
                    Active Table:
                    <span className="font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                      {selectedTables.find(t => `${t.database}:${t.schema}:${t.table}` === selectedTableKey)?.table}
                      &nbsp;→&nbsp;
                      {selectedTables.find(t => `${t.database}:${t.schema}:${t.table}` === selectedTableKey)?.bronze_table ||
                        `BRONZE_${selectedTables.find(t => `${t.database}:${t.schema}:${t.table}` === selectedTableKey)?.table}`}
                    </span>
                  </h4>
                </div>
                <button
                  onClick={addMappingRow}
                  className="flex items-center gap-1.5 px-3 py-2 border border-slate-200 rounded-xl text-xs font-bold hover:bg-slate-50 text-slate-600"
                >
                  <PlusIcon className="w-4 h-4 stroke-[2.5]" /> Add Field Mapping
                </button>
              </div>

              <div className="overflow-x-auto border border-slate-100 rounded-2xl">
                <table className="min-w-full divide-y divide-slate-150">
                  <thead className="bg-slate-50">
                    <tr>
                      <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Source Column / Expression</th>
                      <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Target Column (BRONZE)</th>
                      <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Match Weight (Fuzzy)</th>
                      <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Normalization</th>
                      <th scope="col" className="relative px-4 py-3"><span className="sr-only">Remove</span></th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-slate-100">
                    {currentMappings.map((m, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="px-4 py-3">
                          <input
                            type="text"
                            list="stg-columns-list"
                            value={m.src}
                            onChange={e => updateMappingRow(idx, 'src', e.target.value)}
                            placeholder="Select column or expr: (e.g. expr:NAME1 || ' ' || NAME2)"
                            className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-mono font-medium focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-400 transition-all"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={m.tgt}
                            onChange={e => updateMappingRow(idx, 'tgt', e.target.value)}
                            className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-400 transition-all"
                          >
                            <option value="">-- Select Target Column --</option>
                            {tgtColumns.map(col => (
                              <option key={col} value={col}>{col}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            step="0.05"
                            min="0"
                            max="1"
                            value={m.match_weight === null ? '' : m.match_weight}
                            onChange={e => updateMappingRow(idx, 'match_weight', e.target.value === '' ? null : parseFloat(e.target.value))}
                            placeholder="null = exact match / ID"
                            className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-400 transition-all"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={m.normalize}
                            onChange={e => updateMappingRow(idx, 'normalize', e.target.value)}
                            className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-400 transition-all appearance-none"
                          >
                            <option value="none">None</option>
                            <option value="text">Text Clean (Lower + spaces)</option>
                            <option value="email">Email Normalization</option>
                            <option value="phone">Phone Normalization</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => removeMappingRow(idx)} className="text-slate-400 hover:text-rose-600 transition-colors">
                            <TrashIcon className="w-4.5 h-4.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-48 text-slate-400 italic border border-dashed border-slate-200 rounded-2xl bg-slate-50/30">
              <ArrowsRightLeftIcon className="w-8 h-8 text-slate-350 stroke-[1.5] mb-2 animate-pulse" />
              <p className="text-xs font-semibold">Select a table tab above to configure column mappings.</p>
            </div>
          )}

          <div className="flex justify-between border-t border-slate-100 pt-4">
            <button
              onClick={() => setCurrentStep(2)}
              className="px-5 py-2.5 border border-slate-200 hover:border-slate-350 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white transition-all active:scale-95"
            >
              Back
            </button>
            <button
              onClick={configureMDM}
              disabled={isProcessing}
              className="flex items-center gap-2 px-6 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-bold text-xs transition-all active:scale-95 shadow-md shadow-violet-100"
            >
              {isProcessing && <ArrowPathIcon className="w-4 h-4 animate-spin" />}
              Save Mapping &amp; Run
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════════ STEP 4: EXECUTION DASHBOARD ═══════════════════ */}
      {currentStep === 4 && (
        <div className="space-y-6 text-left animate-fadeIn">
          {/* Back button */}
          <div className="flex">
            <button
              onClick={() => setCurrentStep(3)}
              className="flex items-center gap-1.5 px-4 py-2 border border-slate-200 hover:border-slate-300 rounded-xl text-slate-600 hover:text-slate-800 font-bold text-xs bg-white transition-all active:scale-95"
            >
              <ChevronLeftIcon className="w-3.5 h-3.5 stroke-[2.5]" /> Back to Mapping
            </button>
          </div>
          {/* Controls Card */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-violet-50 border border-violet-100 flex items-center justify-center text-violet-600 shrink-0">
                <PlayIcon className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-black text-slate-800">Trigger MDM Record Unification</h4>
                <p className="text-xs text-slate-450 font-semibold mt-0.5">
                  Execute the Snowflake stage loaders and Snowpark fuzzy matching similarity workflows.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={fetchStatus}
                className="px-4 py-2.5 border border-slate-200 hover:border-slate-350 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white transition-all active:scale-95 flex items-center gap-1.5"
              >
                <ArrowPathIcon className="w-4 h-4" /> Refresh Audit Logs
              </button>
              <button
                onClick={runUnification}
                disabled={isProcessing}
                className="flex items-center justify-center gap-2 px-6 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-black text-xs disabled:bg-slate-350 disabled:cursor-not-allowed transition-all active:scale-95 shadow-md shadow-indigo-100"
              >
                {isProcessing ? (
                  <><ArrowPathIcon className="h-4 w-4 animate-spin" /> Unifying...</>
                ) : (
                  <><SparklesIcon className="h-4 w-4" /> Run MDM Match Pipeline</>
                )}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Audit Logs List */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm lg:col-span-1 flex flex-col h-[500px]">
              <h3 className="text-sm font-bold text-slate-850 uppercase tracking-widest mb-4">Merge Audit Logs</h3>
              <div className="flex-1 overflow-y-auto space-y-3.5 pr-2">
                {executionLogs.length > 0 ? (
                  executionLogs.map((log, idx) => (
                    <div key={idx} className="p-3 border border-slate-100 rounded-xl bg-slate-50/50 hover:bg-slate-50 transition-colors">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono font-bold text-slate-400">Run: {log.run_id ? log.run_id.substring(0, 8) : 'N/A'}</span>
                        <span className={`text-[9px] font-black px-2 py-0.5 rounded-full ${log.status === 'SUCCESS' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-rose-50 text-rose-600 border border-rose-100'
                          }`}>
                          {log.status}
                        </span>
                      </div>
                      <div className="text-[11px] font-semibold text-slate-700">Source: <span className="text-slate-900 font-bold">{log.source_system}</span></div>
                      <div className="text-[10px] font-semibold text-slate-500 mt-1">Inserted: {log.rows_inserted} | Updated: {log.rows_updated}</div>
                      {log.error_message && (
                        <div className="text-[9px] font-semibold text-rose-600 mt-2 bg-rose-50/30 p-2 rounded border border-rose-100/50 break-all">{log.error_message}</div>
                      )}
                      <div className="text-[9px] font-medium text-slate-400 mt-2">{log.timestamp}</div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic font-semibold pt-4">No audit logs found. Run the pipeline first.</p>
                )}
              </div>
            </div>

            {/* Unified Master Entity Preview */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm lg:col-span-2 flex flex-col h-[500px]">
              <h3 className="text-sm font-bold text-slate-850 uppercase tracking-widest mb-4">Unified Master Entity Records</h3>
              <div className="flex-1 overflow-auto border border-slate-100 rounded-2xl bg-slate-50/30">
                {masterRecords.length > 0 ? (() => {
                  const standardKeys = new Set([
                    'MASTER_ID', 'GROUP_NAME', 'SOURCE_IDS', 'SOURCE_SYSTEMS', 
                    'CLUSTER_SIZE', 'MATCH_CONFIDENCE', 'PIPELINE_RUN_ID', 
                    'CREATED_TS', 'ENTITY_DATA'
                  ]);
                  const entityCols = Object.keys(masterRecords[0] || {}).filter(k => !standardKeys.has(k));
                  
                  return (
                    <table className="min-w-full divide-y divide-slate-150">
                      <thead className="bg-slate-50">
                        <tr>
                          <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Master ID</th>
                          {entityCols.map(col => (
                            <th key={col} scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">{col.replace(/_/g, ' ')}</th>
                          ))}
                          <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Matched IDs</th>
                          <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Source Systems</th>
                          <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Confidence</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-slate-100 text-xs font-semibold text-slate-700">
                        {masterRecords.map((r, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/50">
                            <td className="px-4 py-3 font-mono font-bold text-violet-600">{r.MASTER_ID}</td>
                            {entityCols.map(col => (
                              <td key={col} className="px-4 py-3 font-medium">{r[col] ?? ''}</td>
                            ))}
                            <td className="px-4 py-3 font-mono text-[10px] text-slate-500 max-w-[150px] truncate" title={r.SOURCE_IDS}>{r.SOURCE_IDS}</td>
                            <td className="px-4 py-3 font-medium text-slate-500">{r.SOURCE_SYSTEMS}</td>
                            <td className="px-4 py-3">
                              <span className={`text-[9px] font-black px-2 py-0.5 rounded-full ${r.MATCH_CONFIDENCE === 'HIGH' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' :
                                r.MATCH_CONFIDENCE === 'MEDIUM' ? 'bg-amber-50 text-amber-600 border border-amber-100' :
                                  'bg-rose-50 text-rose-600 border border-rose-100'
                                }`}>
                                {r.MATCH_CONFIDENCE || 'HIGH'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  );
                })()
                : (
                  <div className="flex flex-col items-center justify-center h-full text-slate-400 italic">
                    <SparklesIcon className="w-10 h-10 text-slate-350 stroke-[1.5] mb-2 animate-pulse" />
                    <p className="text-xs font-semibold">No unified master records to preview yet.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <datalist id="stg-columns-list">
        {stgColumns.map(col => (
          <option key={col} value={col} />
        ))}
      </datalist>
    </div>
  );
};
