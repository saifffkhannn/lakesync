import { useState, useEffect, useRef } from 'react';
import {
  ShieldCheckIcon,
  TableCellsIcon,
  ArrowsRightLeftIcon,
  PlayIcon
} from '@heroicons/react/24/outline';

import sourceData from './data/source.json';
import cloudData from './data/cloud.json';
import targetData from './data/target.json';
import dataTypeClusters from './data/data_type_clusters.json';
import devConfig from './data/dev_config.json';

import { StepWizard } from './components/StepWizard';
import { CredentialsStep } from './components/CredentialsStep';
import { SelectionStep } from './components/SelectionStep';
import { MappingStep } from './components/MappingStep';
import { ExecutionStep } from './components/ExecutionStep';

const API_BASE = "https://lakesync-gateway.onrender.com";

type TablePair = { id: string; srcTable: string; tgtTable: string; };
type QueueStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'HALTED';
type QueueItem = TablePair & { status: QueueStatus, finalMap: any };

const IngestionUI = ({ onBack }: { onBack: () => void }) => {
  const [step, setStep] = useState(1);
  const [openForms, setOpenForms] = useState<Record<'source' | 'cloud' | 'target', boolean>>({
    source: false,
    cloud: false,
    target: false
  });
  const [platforms] = useState<any>({
    sources: Object.keys(sourceData),
    clouds: Object.keys(cloudData),
    targets: Object.keys(targetData)
  });

  const [selection, setSelection] = useState<any>({
    sourcePlatform: devConfig.sourcePlatform || '',
    cloudPlatform: devConfig.cloudPlatform || '',
    targetPlatform: devConfig.targetPlatform || '',
    loadType: (devConfig as any).loadType || 'INCREMENTAL',
    srcSchema: '',
    tgtSchema: ''
  });

  const [formData, setFormData] = useState<any>({
    source: devConfig.source || {},
    cloud: devConfig.cloud || {},
    target: devConfig.target || {}
  });

  const [config, setConfig] = useState<any>(null);
  const [metadata, setMetadata] = useState<any>({ srcSchemas: [], srcTables: [], tgtSchemas: [], tgtTables: [] });
  const [tablePairs, setTablePairs] = useState<TablePair[]>([]);
  const [currentSrcTable, setCurrentSrcTable] = useState('');
  const [currentTgtTable, setCurrentTgtTable] = useState('');
  const [pairMetadata, setPairMetadata] = useState<Record<string, { srcColumns: any[], tgtColumns: any[] }>>({});
  const [allMappings, setAllMappings] = useState<Record<string, Record<string, string>>>({});
  const [allDefaultValues, setAllDefaultValues] = useState<Record<string, Record<string, string>>>({});
  const [tableConfig, setTableConfig] = useState<Record<string, { primary_keys: string[]; incremental_src_col: string }>>({});
  const [activeMappingId, setActiveMappingId] = useState<string | null>(null);
  const [typeMappings, setTypeMappings] = useState<Record<string, string[]>>({});
  const [batchQueue, setBatchQueue] = useState<QueueItem[]>([]);
  const [logs, setLogs] = useState<string[]>(['[INFO] Service Ready']);
  const [ingestionStatus, setIngestionStatus] = useState<any>({ status: 'IDLE', source_rows: 0, loaded_rows: 0, message: '' });
  const [isProcessing, setIsProcessing] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [shouldDownloadMapping, setShouldDownloadMapping] = useState(false);
  const pollingRef = useRef<any>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const [savedProfiles, setSavedProfiles] = useState<Record<'source' | 'cloud' | 'target', Record<string, any>>>(() => {
    try {
      const stored = localStorage.getItem('lake_sync_profiles');
      if (stored) return JSON.parse(stored);
    } catch (e) {
      console.error("Failed to load saved profiles", e);
    }
    
    // Fallback/Initial seeding from devConfig
    const initial: any = { source: {}, cloud: {}, target: {} };
    if (devConfig.sourcePlatform) {
      initial.source[devConfig.sourcePlatform] = devConfig.source || {};
    }
    if (devConfig.cloudPlatform) {
      initial.cloud[devConfig.cloudPlatform] = devConfig.cloud || {};
    }
    if (devConfig.targetPlatform) {
      initial.target[devConfig.targetPlatform] = devConfig.target || {};
    }
    return initial;
  });

  useEffect(() => {
    localStorage.setItem('lake_sync_profiles', JSON.stringify(savedProfiles));
  }, [savedProfiles]);

  const isFailedStatus = (status: string) => {
    if (!status) return false;
    const s = status.toUpperCase();
    return s === 'FAILED' || s.endsWith('_FAILED');
  };

  const isSuccessStatus = (status: string) => {
    if (!status) return false;
    const s = status.toUpperCase();
    return s === 'COMPLETED' || s === 'SUCCESS';
  };

  useEffect(() => { logsEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logs, ingestionStatus.message]);

  useEffect(() => {
    fetch(`${API_BASE}/config`).then(res => res.json()).then(data => {
      if (data && Object.keys(data).length > 0) setLogs(prev => [...prev, `[INFO] Existing configuration detected`]);
    }).catch(err => console.error("Failed to check existing config", err));
  }, []);

  const currentRunningIndex = batchQueue.findIndex(q => q.status === 'RUNNING');

  useEffect(() => {
    const triggerIngestion = async () => {
      if (batchQueue.some(q => q.status === 'RUNNING')) return;
      if (!batchQueue.some(q => q.status === 'QUEUED')) return;
      setBatchQueue(prev => prev.map(q => q.status === 'QUEUED' ? { ...q, status: 'RUNNING' } : q));
      try {
        await fetch(`${API_BASE}/ingest`, { method: 'POST' });
        setLogs(prev => [...prev, `[INFO] Batch ingestion triggered`]);
      } catch (e) {
        setLogs(prev => [...prev, `[ERROR] Failed to start task: ${e}`]);
        setBatchQueue(prev => prev.map(q => q.status === 'RUNNING' ? { ...q, status: 'FAILED' } : q));
      }
    };
    if (step === 4) {
      if (isSuccessStatus(ingestionStatus.status)) {
        setBatchQueue(prev => prev.map(q => q.status === 'RUNNING' ? { ...q, status: 'COMPLETED' } : q));
      } else if (isFailedStatus(ingestionStatus.status)) {
        setBatchQueue(prev => prev.map(q => q.status === 'RUNNING' ? { ...q, status: 'FAILED' } : q));
      } else if (ingestionStatus.status === 'IDLE' && batchQueue.some(q => q.status === 'QUEUED')) {
        triggerIngestion();
      }
    }
  }, [step, ingestionStatus.status, batchQueue]);

  useEffect(() => {
    if (step === 4) {
      pollingRef.current = setInterval(async () => {
        if (selection.loadType === 'FULL' || currentRunningIndex !== -1) {
          try {
            const endpoint = selection.loadType === 'FULL' ? `${API_BASE}/migration-status` : `${API_BASE}/ingest/status`;
            const res = await fetch(endpoint);
            const data = await res.json();
            
            let normalizedData = data;
            if (selection.loadType === 'FULL') {
              // Check if any table is in failed/error state
              const hasFailed = data.table_status?.some((t: any) => ['failed', 'extraction_failed', 'upload_failed', 'table_creation_failed', 'load_failed', 'validation_failed'].includes(t.status?.toLowerCase()));
              const allDone = data.table_status?.every((t: any) => ['completed', 'success', 'skipped'].includes(t.status?.toLowerCase()));
              
              normalizedData = {
                status: hasFailed ? 'FAILED' : (allDone || data.progress === 100) ? 'COMPLETED' : 'RUNNING',
                progress: data.progress,
                details: data.table_status,
                logs: data.logs,
                message: data.table_status?.find((t: any) => ['extracting', 'uploading', 'creating_table', 'loading'].includes(t.status?.toLowerCase())) 
                  ? `Table: ${data.table_status.find((t: any) => ['extracting', 'uploading', 'creating_table', 'loading'].includes(t.status?.toLowerCase())).table}`
                  : ''
              };
            }

            if (JSON.stringify(normalizedData) !== JSON.stringify(ingestionStatus)) {
              setIngestionStatus((prev: any) => {
                let newProgress = normalizedData.progress ?? 0;
                if (
                  normalizedData.status !== 'IDLE' &&
                  normalizedData.status !== 'INITIALIZING' &&
                  prev &&
                  prev.progress !== undefined &&
                  prev.status !== 'COMPLETED' &&
                  prev.status !== 'FAILED'
                ) {
                  newProgress = Math.max(prev.progress, newProgress);
                }
                return { ...normalizedData, progress: newProgress };
              });
              if (normalizedData.logs && Array.isArray(normalizedData.logs)) {
                setLogs(prev => {
                  const initialLogs = prev.filter(l => l.startsWith('['));
                  const uniqueLogs = [...initialLogs];
                  normalizedData.logs.forEach((log: string) => {
                    if (!uniqueLogs.includes(log)) {
                      uniqueLogs.push(log);
                    }
                  });
                  return uniqueLogs;
                });
              }
            }
          } catch (e) { }
        }
      }, 2000);
    }
    return () => clearInterval(pollingRef.current);
  }, [step, currentRunningIndex, ingestionStatus, selection.loadType]);

  const handleInputChange = (category: 'source' | 'cloud' | 'target', key: string, value: string) => {
    setFormData((prev: any) => ({ ...prev, [category]: { ...prev[category], [key]: value } }));
  };

  const handlePlatformChange = (category: 'sourcePlatform' | 'cloudPlatform' | 'targetPlatform', value: string) => {
    setSelection((prev: any) => ({ ...prev, [category]: value }));
    const formCategory = category.replace('Platform', '') as 'source' | 'cloud' | 'target';
    
    // Load saved credentials for this platform if they exist, otherwise set empty
    const saved = savedProfiles[formCategory]?.[value];
    setFormData((prev: any) => ({ ...prev, [formCategory]: saved || {} }));

    const nextSelection = { ...selection, [category]: value };
    if (nextSelection.sourcePlatform && nextSelection.targetPlatform) {
      loadTypeMappings(nextSelection.sourcePlatform, nextSelection.targetPlatform);
    }
  };

  const loadTypeMappings = async (src: string, tgt: string) => {
    const fileName = `${src.toLowerCase()}_${tgt.toLowerCase()}.csv`;
    try {
      const response = await fetch(`/data/${fileName}`);
      if (!response.ok) return;
      const text = await response.text();
      const lines = text.split('\n').slice(1);
      const map: Record<string, string[]> = {};
      lines.forEach(line => {
        if (!line.trim()) return;
        const [s, t] = line.split(',').map(x => x.trim().replace(/"/g, '').toLowerCase());
        if (!map[s]) map[s] = [];
        map[s].push(t);
      });
      setTypeMappings(map);
    } catch (e) { console.warn("Could not load type mappings:", e); }
  };

  // ─── Normalize: lowercase + strip precision e.g. NUMBER(10,0) → number ──
  const normalizeType = (t: string): string =>
    t.toLowerCase().replace(/\s*\(.*?\)/g, '').trim();

  // ─── Resolve a type to its logical cluster from data_type_clusters.json ──
  const getCluster = (raw: string): string | null => {
    const n = normalizeType(raw);
    for (const [cluster, members] of Object.entries(dataTypeClusters.clusters)) {
      if ((members as string[]).map(m => m.toLowerCase()).includes(n)) return cluster;
    }
    return null;
  };

  // ─── Is this type numeric? ────────────────────────────────────────────────
  const isNumericType = (raw: string): boolean => {
    const n = normalizeType(raw);
    if (getCluster(n) === 'number') return true;
    return /^(int|integer|bigint|smallint|tinyint|numeric|decimal|float|double|real|long|number|float64|int64)\b/.test(n);
  };

  // ─── Is this type string-like? ────────────────────────────────────────────
  const isStringType = (raw: string): boolean => {
    const n = normalizeType(raw);
    if (getCluster(n) === 'text') return true;
    return ['string', 'varchar', 'nvarchar', 'char', 'nchar', 'text', 'ntext'].includes(n);
  };

  // ─── Core compatibility — cluster-aware, numeric widening, CSV-backed ────
  const isTypeCompatible = (srcType: string, tgtType: string): boolean => {
    if (!srcType || !tgtType) return true;

    const s = normalizeType(srcType);
    const t = normalizeType(tgtType);

    // Exact match after normalization
    if (s === t) return true;

    // CSV direct mapping (e.g. datetime → timestamp, datetime → timestamp_ntz)
    if (typeMappings[s]?.map(normalizeType).includes(t)) return true;

    const srcCluster = getCluster(s);
    const tgtCluster = getCluster(t);

    // Same cluster → always compatible
    // datetime ↔ timestamp ↔ timestamp_ntz ↔ timestamp_tz ↔ timestamp_ltz
    // int ↔ bigint ↔ number ↔ float ↔ double  etc.
    if (srcCluster && tgtCluster && srcCluster === tgtCluster) return true;

    // Numeric widening: int→float, number→bigint, int→double etc. all safe
    if (isNumericType(s) && isNumericType(t)) return true;

    // date → datetime is safe (implicit 00:00:00 padding)
    if (srcCluster === 'date' && tgtCluster === 'datetime') return true;

    // Hard blocks — never allow these cross-cluster casts
    if (isNumericType(s) && isStringType(t)) return false;
    if (isStringType(s) && isNumericType(t)) return false;
    if (isStringType(s) && (tgtCluster === 'datetime' || tgtCluster === 'date' || tgtCluster === 'boolean')) return false;
    if (isNumericType(s) && (tgtCluster === 'datetime' || tgtCluster === 'date' || tgtCluster === 'boolean')) return false;

    return false;
  };

  // ─── Custom input metadata — type-aware, Parquet-safe formats ────────────
  const getCustomInputMeta = (dataType: string): {
    inputType: string;
    placeholder: string;
    hint: string;
  } => {
    if (!dataType) return { inputType: 'text', placeholder: 'Enter constant value…', hint: 'Any value is accepted as a literal' };
    const n = normalizeType(dataType);
    const cluster = getCluster(n);

    if (cluster === 'datetime' || n.includes('timestamp') || n.includes('datetime')) {
      return {
        inputType: 'datetime-local',
        placeholder: 'YYYY-MM-DDTHH:MM',
        hint: 'Select date & time for custom value'
      };
    }
    if (cluster === 'date' || n.includes('date')) {
      return {
        inputType: 'date',
        placeholder: 'YYYY-MM-DD',
        hint: 'Select date for custom value'
      };
    }
    if (cluster === 'number' || isNumericType(n)) {
      const isInteger = /^(int|integer|bigint|smallint|tinyint|int64)\b/.test(n);
      return {
        inputType: 'text',
        placeholder: isInteger ? '42' : '3.14',
        hint: isInteger ? 'Integer constant (e.g. 42, 0, -1)' : 'Numeric constant (e.g. 3.14, 0.0)'
      };
    }
    if (cluster === 'boolean') {
      return { inputType: 'text', placeholder: 'true', hint: 'Boolean literal: true or false' };
    }
    if (cluster === 'json') {
      return { inputType: 'text', placeholder: '{"key": "value"}', hint: 'JSON literal' };
    }
    if (['binary', 'varbinary', 'bytes', 'image'].includes(n)) {
      return { inputType: 'text', placeholder: 'Base64 encoded string', hint: 'Base64 binary value' };
    }
    return { inputType: 'text', placeholder: 'Enter constant value…', hint: 'Any literal value (string, number, date, etc.)' };
  };

  // Helper to pre-format stored datetime/date strings for browser pickers
  const getInputValue = (rawVal: any, inputType: string): string => {
    if (rawVal === undefined || rawVal === null) return '';
    const str = String(rawVal).trim();
    if (inputType === 'datetime-local') {
      let formatted = str;
      if (formatted.includes(' ')) {
        formatted = formatted.replace(' ', 'T');
      }
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(formatted)) {
        return formatted.substring(0, 16); // format YYYY-MM-DDTHH:MM
      }
      return formatted;
    }
    if (inputType === 'date') {
      if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
        return str.substring(0, 10); // format YYYY-MM-DD
      }
    }
    return str;
  };

  // ─── Validate & coerce custom constant — permissive: any raw value passes through ───
  const validateCustomValue = (
    val: string, dataType: string, _colName: string, _tableName: string, _pairId: string
  ): { ok: false } | { ok: true; coerced: any } => {
    const n = normalizeType(dataType);
    const cluster = getCluster(n);
    const trimmed = val.trim();

    // Boolean — coerce to true/false booleans
    if (cluster === 'boolean') {
      if (trimmed.toLowerCase() === 'true') return { ok: true, coerced: true };
      if (trimmed.toLowerCase() === 'false') return { ok: true, coerced: false };
      // Non-standard boolean: pass as string literal
      return { ok: true, coerced: trimmed };
    }

    // Number — coerce if possible, else pass as string
    if (cluster === 'number' || isNumericType(n)) {
      const isInteger = /^(int|integer|bigint|smallint|tinyint|int64)\b/.test(n);
      if (isInteger && /^-?[0-9]+$/.test(trimmed)) return { ok: true, coerced: parseInt(trimmed, 10) };
      const num = Number(trimmed);
      if (!isNaN(num)) return { ok: true, coerced: num };
      // Non-numeric input for numeric col: pass through as literal string
      return { ok: true, coerced: trimmed };
    }

    // All other types (datetime, date, string, binary, json, etc.) — accept as-is
    return { ok: true, coerced: trimmed };
  };


  const saveConfig = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    setConnectionError(null);
    const payload = {
      source: { ...formData.source, platform: selection.sourcePlatform },
      target: { ...formData.target, platform: selection.targetPlatform },
      cloud: { ...formData.cloud, platform: selection.cloudPlatform },
      load_type: selection.loadType
    };
    try {
      const response = await fetch(`${API_BASE}/config`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (!response.ok) {
        const errDetail = await response.json().catch(() => ({ detail: 'Failed to save config' }));
        throw new Error(errDetail.detail || 'Failed to save config');
      }
      setConfig(payload);
      setLogs(prev => [...prev, `[INFO] Configuration saved successfully`]);
      
      let srcS = [];
      let tgtS = [];
      if (selection.loadType === 'FULL') {
        const srcRes = await fetch(`${API_BASE}/source/schemas`);
        if (!srcRes.ok) {
          const errDetail = await srcRes.json().catch(() => ({ detail: 'Failed to fetch source schemas' }));
          throw new Error(`Source connection failed: ${errDetail.detail || 'Invalid credentials or connection timeout'}`);
        }
        srcS = await srcRes.json();
      } else {
        const [srcRes, tgtRes] = await Promise.all([
          fetch(`${API_BASE}/source/schemas`),
          fetch(`${API_BASE}/target/schemas`)
        ]);
        if (!srcRes.ok) {
          const errDetail = await srcRes.json().catch(() => ({ detail: 'Failed to fetch source schemas' }));
          throw new Error(`Source connection failed: ${errDetail.detail || 'Invalid credentials or connection timeout'}`);
        }
        if (!tgtRes.ok) {
          const errDetail = await tgtRes.json().catch(() => ({ detail: 'Failed to fetch target schemas' }));
          throw new Error(`Target connection failed: ${errDetail.detail || 'Invalid credentials or connection timeout'}`);
        }
        srcS = await srcRes.json();
        tgtS = await tgtRes.json();
      }
      setMetadata((prev: any) => ({ ...prev, srcSchemas: srcS, tgtSchemas: tgtS }));
      
      if (selection.loadType === 'FULL') {
        const metadataUrl = `${API_BASE}/fetch-metadata?source=${selection.sourcePlatform}&cloud=${selection.cloudPlatform}&target=${selection.targetPlatform}`;
        const res = await fetch(metadataUrl);
        if (!res.ok) {
          const errDetail = await res.json().catch(() => ({ detail: 'Failed to fetch metadata' }));
          throw new Error(`Metadata retrieval failed: ${errDetail.detail || 'Invalid credentials'}`);
        }
        const data = await res.json();
        const mappedTables = data.map((t: any) => ({
          database: t.DB_NAME || t.DATABASE || t.database || "",
          schema: t.TABLE_SCHEMA || t.SCHEMA || t.schema,
          table: t.TABLE_NAME || t.TABLE || t.table,
          primaryKey: t.PRIMARY_KEY_COLUMNS || t.PRIMARY_KEY || t.primaryKey || ""
        }));
        setMetadata((prev: any) => ({ ...prev, fullLoadTables: mappedTables }));
      }
      
      if (selection.sourcePlatform.toLowerCase() === 'mysql' && selection.loadType !== 'FULL') {
        await loadTables('source', payload.source.database || '');
      }
      setStep(2);
    } catch (err: any) {
      setLogs(prev => [...prev, `[ERROR] Failed to connect: ${err.message || err}`]);
      setConnectionError(err.message || 'Failed to connect. Please check your credentials.');
    } finally { setIsProcessing(false); }
  };

  const loadTables = async (type: 'source' | 'target', schema: string) => {
    try {
      const res = await fetch(`${API_BASE}/${type}/tables?schema=${schema}`);
      const tables = await res.json();
      setMetadata((prev: any) => ({ ...prev, [type === 'source' ? 'srcTables' : 'tgtTables']: tables }));
      setSelection((prev: any) => ({ ...prev, [type === 'source' ? 'srcSchema' : 'tgtSchema']: schema }));
    } catch (err) { setLogs(prev => [...prev, `[ERROR] Failed to load tables for ${schema}: ${err}`]); }
  };

  const addTablePair = () => {
    if (currentSrcTable && currentTgtTable) {
      setTablePairs(prev => [...prev, { id: Date.now().toString(), srcTable: currentSrcTable, tgtTable: currentTgtTable }]);
      setCurrentSrcTable('');
      setCurrentTgtTable('');
    }
  };

  const startFullLoadMigration = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    try {
      const selections = (metadata.fullLoadTables || []).filter((t: any) =>
        tablePairs.some(p => p.srcTable === t.table)
      );
      if (selections.length === 0) {
        alert("Please select at least one table.");
        return;
      }
      
      const savePayload = {
        source: selection.sourcePlatform,
        selections: selections.map((s: any) => ({
          source: selection.sourcePlatform.toUpperCase(),
          database: s.database,
          schema_name: s.schema,
          table: s.table,
          primary_key: s.primaryKey || ""
        }))
      };
      
      const saveRes = await fetch(`${API_BASE}/save-metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(savePayload)
      });
      if (!saveRes.ok) {
        const err = await saveRes.json();
        alert(`Error saving metadata: ${err.detail || "Failed"}`);
        return;
      }

      const startPayload = {
        source: selection.sourcePlatform,
        cloud: selection.cloudPlatform,
        target: selection.targetPlatform,
        metadata_filename: `${selection.sourcePlatform.toLowerCase()}_metadata.csv`
      };
      const startRes = await fetch(`${API_BASE}/start-extraction`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(startPayload)
      });
      if (!startRes.ok) {
        const err = await startRes.json();
        alert(`Migration failed: ${err.detail || "Failed"}`);
        return;
      }

      const queueData = tablePairs.map(p => ({
        id: p.id,
        srcTable: p.srcTable,
        tgtTable: p.tgtTable,
        status: 'QUEUED' as const,
        finalMap: {}
      }));
      setBatchQueue(queueData);
      setLogs(['[INFO] Full Load Ingestion Started']);
      setIngestionStatus({ status: 'INITIALIZING', source_rows: 0, loaded_rows: 0, message: '', progress: 0 });
      setStep(4);
    } catch (err: any) {
      alert(`Critical error starting full load: ${err.message || err}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const prepareBatchMapping = async () => {
    if (selection.loadType === 'FULL') {
      await startFullLoadMigration();
      return;
    }
    if (isProcessing) return;
    setIsProcessing(true);
    try {
      setStep(3);
      if (tablePairs.length > 0) await loadColumnsForPair(tablePairs[0]);
      else setActiveMappingId(null);
    } finally { setIsProcessing(false); }
  };

  const loadColumnsForPair = async (pair: TablePair) => {
    setActiveMappingId(pair.id);
    if (!pairMetadata[pair.id]) {
      try {
        const [sRes, tRes] = await Promise.all([
          fetch(`${API_BASE}/source/columns?schema=${selection.srcSchema}&table=${pair.srcTable}`).then(r => r.json()),
          fetch(`${API_BASE}/target/columns?schema=${selection.tgtSchema}&table=${pair.tgtTable}`).then(r => r.json())
        ]);
        const srcC = sRes;
        const tgtC = tRes;
        setPairMetadata(prev => ({ ...prev, [pair.id]: { srcColumns: srcC, tgtColumns: tgtC } }));
        const newMapping: Record<string, string> = {};
        tgtC.forEach((col: any) => {
          const match = srcC.find((s: any) => s.column_name.toLowerCase() === col.column_name.toLowerCase());
          const hasDefault = col.default !== null && col.default !== undefined && col.default !== '';
          if (match) newMapping[col.column_name] = match.column_name;
          else if (col.nullable === 'YES' || col.nullable === true || hasDefault) newMapping[col.column_name] = '_NULL_';
          else newMapping[col.column_name] = '';
        });
        const commonWatermarks = ['updated_at', 'modified_at', 'modified_timestamp', 'last_modified', 'timestamp', 'load_date'];
        const autoWatermarkSrc = srcC.find((c: any) => commonWatermarks.includes(c.column_name.toLowerCase()))?.column_name || '';
        setAllDefaultValues(prev => ({ ...prev, [pair.id]: {} }));
        const defaultPks = srcC.filter((c: any) => c.is_primary_key).map((c: any) => c.column_name);
        setAllMappings(prev => ({ ...prev, [pair.id]: newMapping }));
        setTableConfig(prev => {
          if (!prev[pair.id]) return { ...prev, [pair.id]: { primary_keys: defaultPks, incremental_src_col: autoWatermarkSrc } };
          return { ...prev, [pair.id]: { ...prev[pair.id], primary_keys: prev[pair.id].primary_keys.length > 0 ? prev[pair.id].primary_keys : defaultPks, incremental_src_col: prev[pair.id].incremental_src_col || autoWatermarkSrc } };
        });
      } catch (err) { setLogs(prev => [...prev, `[ERROR] Failed to load columns: ${err}`]); }
    }
  };

  const downloadAndBeginBatch = () => {
    if (isProcessing) return;
    setIsProcessing(true);
    try {
      const queueData: QueueItem[] = [];
      for (const pair of tablePairs) {
        const meta = pairMetadata[pair.id];
        if (!meta) { alert(`Please configure mapped columns for table ${pair.srcTable}`); setActiveMappingId(pair.id); return; }
        const tcfg = tableConfig[pair.id] || { primary_keys: [], incremental_src_col: '' };
        let watermarkCol = tcfg.incremental_src_col;
        if (selection.loadType === 'FULL' && !watermarkCol) {
          watermarkCol = meta?.srcColumns[0]?.column_name || '';
        }
        if (!watermarkCol) { alert(`Please configure the Watermark column for table ${pair.srcTable}`); setActiveMappingId(pair.id); return; }
        const maps = allMappings[pair.id] || {};
        const defaults = allDefaultValues[pair.id] || {};
        const finalMap: any = {};
        for (const tCol of meta.tgtColumns) {
          let m = maps[tCol.column_name];
          const hasDefault = tCol.default !== null && tCol.default !== undefined && tCol.default !== '';
          const isNullable = tCol.nullable === 'YES' || tCol.nullable === true;
          const isOptional = isNullable || hasDefault;
          if (!m || m === '') { if (isOptional) continue; alert(`Target column "${tCol.column_name}" in ${pair.tgtTable} is required but not mapped.`); setActiveMappingId(pair.id); return; }
          if (m === '_CUSTOM_' && (!defaults[tCol.column_name] || !defaults[tCol.column_name].trim())) { alert(`Please enter a custom value for target column "${tCol.column_name}" in ${pair.tgtTable}.`); setActiveMappingId(pair.id); return; }
          if (m === '_NULL_') {
            if (!isNullable) { alert(`Target column "${tCol.column_name}" in ${pair.tgtTable} cannot be NULL.`); setActiveMappingId(pair.id); return; }
            finalMap[tCol.column_name] = 'NULL';
          } else if (m === '_CUSTOM_') {
            // ── Use cluster-aware validation instead of old logicalType lookup ──
            let rawVal = defaults[tCol.column_name] || '';
            // If it's a calendar datetime-local output (e.g. 2026-05-27T15:45), format to SQL timestamp
            if (rawVal.includes('T')) {
              rawVal = rawVal.replace('T', ' ');
              // Add seconds if not present
              if (rawVal.length === 16) rawVal += ':00';
            }
            const result = validateCustomValue(rawVal, tCol.data_type, tCol.column_name, pair.tgtTable, pair.id);
            if (!result.ok) return;
            finalMap[tCol.column_name] = result.coerced;
          } else { finalMap[tCol.column_name] = m; }
        }
        queueData.push({ ...pair, status: 'QUEUED', finalMap, primary_keys: tcfg.primary_keys, incremental_src_col: watermarkCol } as any);
      }
      const fullPayload = queueData.map((q: any) => ({
        src_db: config.source.database || config.source.project_id || '',
        src_schema: selection.srcSchema || config.source.schema || config.source.dataset_id || '',
        src_table: q.srcTable,
        tgt_db: config.target.database || config.target.project_id || config.target.catalog || '',
        tgt_schema: selection.tgtSchema || config.target.schema || config.target.dataset_id || '',
        tgt_table: q.tgtTable,
        column_map: q.finalMap,
        source_columns: pairMetadata[q.id]?.srcColumns.map((c: any) => c.column_name) || [],
        target_columns: pairMetadata[q.id]?.tgtColumns.map((c: any) => c.column_name) || [],
        incremental_src_col: q.incremental_src_col || '',
        primary_keys: q.primary_keys || []
      }));
      if (shouldDownloadMapping) {
        const headers = ["src_db", "src_schema", "src_table", "tgt_db", "tgt_schema", "tgt_table", "column_map_json", "source_columns_json", "target_columns_json", "incremental_src_col", "primary_keys"];
        const csvContent = [headers.join(","), ...fullPayload.map((row: any) => [row.src_db, row.src_schema, row.src_table, row.tgt_db, row.tgt_schema, row.tgt_table, `"${JSON.stringify(row.column_map).replace(/"/g, '""')}"`, `"${JSON.stringify(row.source_columns || []).replace(/"/g, '""')}"`, `"${JSON.stringify(row.target_columns || []).replace(/"/g, '""')}"`, row.incremental_src_col, `"${JSON.stringify(row.primary_keys || []).replace(/"/g, '""')}"`].join(","))].join("\n");
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `mapping_batch_${Date.now()}.csv`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
      }
      fetch(`${API_BASE}/mapping/batch`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(fullPayload) })
        .then(async res => {
          if (res.ok) setLogs(prev => [...prev, `[INFO] ${fullPayload.length} table mappings uploaded to backend`]);
          else { const errData = await res.json().catch(() => ({ detail: res.statusText })); setLogs(prev => [...prev, `[ERROR] Failed to upload mappings: ${errData.detail || res.statusText}`]); }
        }).catch(err => setLogs(prev => [...prev, `[ERROR] Backend connection failed: ${err.message}`]));
      setBatchQueue(queueData);
      setIngestionStatus({ status: 'IDLE', source_rows: 0, loaded_rows: 0, message: '', progress: 0 });
      setStep(4);
    } catch (err: any) { alert(`Critical error starting batch: ${err.message || err}`); console.error(err); }
    finally { setIsProcessing(false); }
  };

  const renderFields = (category: 'source' | 'cloud' | 'target', platform: string) => {
    if (!platform) return null;
    let fields: Record<string, string> = {};
    if (category === 'source') fields = (sourceData as any)[platform];
    if (category === 'cloud') fields = (cloudData as any)[platform];
    if (category === 'target') fields = (targetData as any)[platform];
    return Object.keys(fields).map(key => (
      <div key={key} className="space-y-1.5">
        <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest">{key.replace(/_/g, ' ')}</label>
        <input
          type={key.includes('password') || key.includes('secret') ? 'password' : 'text'}
          placeholder={`Enter ${key.replace(/_/g, ' ')}`}
          value={formData[category][key] || ''}
          onChange={(e) => handleInputChange(category, key, e.target.value)}
          className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all"
        />
      </div>
    ));
  };

  const getStatusProgress = () => {
    if (isFailedStatus(ingestionStatus.status)) {
      return ingestionStatus.progress !== undefined ? ingestionStatus.progress : 100;
    }
    if (ingestionStatus.progress !== undefined) {
      return ingestionStatus.progress;
    }
    const stages = ['IDLE', 'INITIALIZING', 'EXTRACTING', 'UPLOADING', 'STAGING', 'LOADING', 'COMPLETED'];
    const currentIdx = stages.indexOf(ingestionStatus.status);
    return Math.max(0, currentIdx >= 0 ? (currentIdx / (stages.length - 1)) * 100 : 0);
  };

  const steps = [
    { id: 1, label: 'Credentials', icon: ShieldCheckIcon },
    { id: 2, label: 'Selection', icon: TableCellsIcon },
    { id: 3, label: 'Mapping', icon: ArrowsRightLeftIcon },
    { id: 4, label: 'Ingestion', icon: PlayIcon },
  ];

  return (
    <div className="min-h-screen bg-slate-50/70">
      {/* ── Step Wizard Bar ── */}
      <StepWizard steps={steps} step={step} setStep={setStep} />

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* ══ STEP 1 ══ */}
        {step === 1 && (
          <CredentialsStep
            onBack={onBack}
            selection={selection}
            setSelection={setSelection}
            formData={formData}
            setFormData={setFormData}
            openForms={openForms}
            setOpenForms={setOpenForms}
            platforms={platforms}
            renderFields={renderFields}
            saveConfig={saveConfig}
            isProcessing={isProcessing}
            savedProfiles={savedProfiles}
            setSavedProfiles={setSavedProfiles}
            handlePlatformChange={handlePlatformChange}
            connectionError={connectionError}
            setConnectionError={setConnectionError}
          />
        )}

        {/* ══ STEP 2 ══ */}
        {step === 2 && (
          <SelectionStep
            selection={selection}
            metadata={metadata}
            tablePairs={tablePairs}
            setTablePairs={setTablePairs}
            currentSrcTable={currentSrcTable}
            setCurrentSrcTable={setCurrentSrcTable}
            currentTgtTable={currentTgtTable}
            setCurrentTgtTable={setCurrentTgtTable}
            loadTables={loadTables}
            addTablePair={addTablePair}
            prepareBatchMapping={prepareBatchMapping}
            isProcessing={isProcessing}
            setStep={setStep}
          />
        )}

        {/* ══ STEP 3 ══ */}
        {step === 3 && (
          <MappingStep
            selection={selection}
            tablePairs={tablePairs}
            pairMetadata={pairMetadata}
            allMappings={allMappings}
            setAllMappings={setAllMappings}
            allDefaultValues={allDefaultValues}
            setAllDefaultValues={setAllDefaultValues}
            tableConfig={tableConfig}
            setTableConfig={setTableConfig}
            activeMappingId={activeMappingId}
            setActiveMappingId={setActiveMappingId}
            loadColumnsForPair={loadColumnsForPair}
            downloadAndBeginBatch={downloadAndBeginBatch}
            shouldDownloadMapping={shouldDownloadMapping}
            setShouldDownloadMapping={setShouldDownloadMapping}
            isTypeCompatible={isTypeCompatible}
            getCustomInputMeta={getCustomInputMeta}
            getInputValue={getInputValue}
            setStep={setStep}
          />
        )}

        {/* ══ STEP 4 ══ */}
        {step === 4 && (
          <ExecutionStep
            ingestionStatus={ingestionStatus}
            batchQueue={batchQueue}
            logs={logs}
            logsEndRef={logsEndRef}
            isSuccessStatus={isSuccessStatus}
            isFailedStatus={isFailedStatus}
            getStatusProgress={getStatusProgress}
            onBack={onBack}
            setStep={setStep}
            API_BASE={API_BASE}
            loadType={selection.loadType}
          />
        )}
      </div>
    </div>
  );
};

export default IngestionUI;
