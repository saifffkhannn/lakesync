const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

// ── Color Palette (Snowflake-inspired) ────────────────────────────────────────
const C = {
  snowBlue:   "29B5E8",   // Snowflake brand blue
  darkBlue:   "0A2342",   // Deep navy
  midBlue:    "0D3B6E",   // Mid navy
  lightBlue:  "E8F6FD",   // Very light blue tint
  white:      "FFFFFF",
  offWhite:   "F7FBFE",
  slate:      "4A5568",
  lightSlate: "718096",
  border:     "B2D8EE",
  accent:     "00C2E0",   // Cyan accent
  green:      "38A169",
  orange:     "DD6B20",
  purple:     "6B46C1",
  red:        "E53E3E",
  cardBg:     "EEF7FC",
  darkCard:   "102A4C",
};

// ── Icon helper ───────────────────────────────────────────────────────────────
async function iconPng(iconSet, iconName, color = "#FFFFFF", size = 256) {
  const icons = require(`react-icons/${iconSet}`);
  const Comp = icons[iconName];
  if (!Comp) return null;
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Comp, { color, size: String(size) })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ── Badge helper ──────────────────────────────────────────────────────────────
function badge(slide, x, y, label, fillColor, textColor = "FFFFFF", w = 1.4, h = 0.28) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.08,
    fill: { color: fillColor }, line: { color: fillColor, width: 0 } });
  slide.addText(label, { x, y, w, h, fontSize: 8, bold: true, color: textColor,
    align: "center", valign: "middle", margin: 0 });
}

// ── Section pill ──────────────────────────────────────────────────────────────
function pill(slide, x, y, label) {
  slide.addShape("roundRect", { x, y, w: 1.6, h: 0.22, rectRadius: 0.1,
    fill: { color: C.snowBlue }, line: { color: C.snowBlue } });
  slide.addText(label, { x, y, w: 1.6, h: 0.22, fontSize: 7.5, bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0 });
}

// ── Card helper ───────────────────────────────────────────────────────────────
function card(slide, x, y, w, h, bg = C.white) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.1,
    fill: { color: bg }, line: { color: C.border, width: 0.5 },
    shadow: { type: "outer", color: "000000", blur: 4, offset: 1, angle: 135, opacity: 0.08 } });
}

// ── Left accent bar ───────────────────────────────────────────────────────────
function accentCard(slide, x, y, w, h, accentColor = C.snowBlue) {
  card(slide, x, y, w, h);
  slide.addShape("RECTANGLE", { x, y, w: 0.05, h,
    fill: { color: accentColor }, line: { color: accentColor } });
}

// ── Slide number footer ───────────────────────────────────────────────────────
function footer(slide, n, total) {
  slide.addText(`${n} / ${total}`, {
    x: 8.8, y: 5.3, w: 0.9, h: 0.2, fontSize: 8, color: C.lightSlate, align: "right" });
}

// ── Slide title ───────────────────────────────────────────────────────────────
function slideTitle(slide, title, sub = "") {
  slide.addText(title, {
    x: 0.45, y: 0.22, w: 9.1, h: 0.52, fontSize: 20, bold: true,
    color: C.darkBlue, align: "left", valign: "middle", margin: 0 });
  if (sub) {
    slide.addText(sub, { x: 0.45, y: 0.74, w: 9.1, h: 0.22, fontSize: 10,
      color: C.lightSlate, align: "left", margin: 0 });
  }
  // Thin separator
  slide.addShape("RECTANGLE", { x: 0.45, y: 0.97, w: 9.1, h: 0.018,
    fill: { color: C.border }, line: { color: C.border } });
}

// ── Main build ────────────────────────────────────────────────────────────────
async function buildPptx() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title = "Snowflake Incremental Ingestion Engine";

  // Pre-render icons
  const iDB     = await iconPng("fa", "FaDatabase",     "#FFFFFF");
  const iCloud  = await iconPng("fa", "FaCloud",        "#FFFFFF");
  const iPython = await iconPng("fa", "FaPython",       "#FFFFFF");
  const iSnow   = await iconPng("fa", "FaSnowflake",    "#FFFFFF");
  const iGear   = await iconPng("fa", "FaCogs",         "#FFFFFF");
  const iFile   = await iconPng("fa", "FaFileAlt",      "#FFFFFF");
  const iCheck  = await iconPng("fa", "FaCheckCircle",  "#38A169");
  const iArrow  = await iconPng("fa", "FaArrowRight",   "#29B5E8");
  const iMerge  = await iconPng("fa", "FaCodeBranch",   "#FFFFFF");
  const iTable  = await iconPng("fa", "FaTable",        "#FFFFFF");
  const iLock   = await iconPng("fa", "FaLock",         "#FFFFFF");
  const iWater  = await iconPng("fa", "FaTint",         "#FFFFFF");
  const iCost   = await iconPng("fa", "FaDollarSign",   "#FFFFFF");
  const iLog    = await iconPng("fa", "FaClipboardList","#FFFFFF");

  const TOTAL = 10;

  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 1 — TITLE
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.darkBlue };

    // Big blue accent block left
    s.addShape("RECTANGLE", { x: 0, y: 0, w: 0.35, h: 5.625,
      fill: { color: C.snowBlue }, line: { color: C.snowBlue } });

    // Snowflake logo-ish circles (decorative)
    s.addShape("OVAL", { x: 7.8, y: -0.6, w: 3.2, h: 3.2,
      fill: { color: "0D3B6E" }, line: { color: "0D3B6E" } });
    s.addShape("OVAL", { x: 8.5, y: 2.8, w: 2.0, h: 2.0,
      fill: { color: "081E3F" }, line: { color: "081E3F" } });

    // Snowflake icon
    if (iSnow) s.addImage({ data: iSnow, x: 0.6, y: 1.3, w: 0.8, h: 0.8 });

    s.addText("High-Performance Snowflake", {
      x: 0.6, y: 2.1, w: 8.5, h: 0.65, fontSize: 30, bold: true,
      color: C.white, margin: 0 });
    s.addText("Incremental Ingestion Engine", {
      x: 0.6, y: 2.72, w: 8.5, h: 0.65, fontSize: 30, bold: true,
      color: C.snowBlue, margin: 0 });

    s.addText("Metadata-driven, cost-optimised data ingestion · Python · Snowflake MERGE · Parquet", {
      x: 0.6, y: 3.5, w: 8.5, h: 0.3, fontSize: 11, color: "A0C4D8", margin: 0 });

    // Tag pills
    const tags = ["Efficiency","Compute Optimisation","Storage Archiving","Data Integrity"];
    tags.forEach((t, i) => badge(s, 0.6 + i * 2.1, 4.2, t, C.snowBlue, C.white, 1.9, 0.3));

    s.addText("Data Engineering Team  ·  2025", {
      x: 0.6, y: 5.1, w: 4, h: 0.25, fontSize: 8.5, color: "6A9BB8", margin: 0 });
  }

  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 2 — PROBLEM STATEMENT
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    slideTitle(s, "The Problem Statement", "Why we built this");
    footer(s, 2, TOTAL);

    const problems = [
      { icon: iCost, color: C.red,    title: "Exponential Compute Costs",
        body: "Full table scans rewrite entire target tables, burning Snowflake warehouse credits." },
      { icon: iCloud, color: C.orange, title: "Network Congestion",
        body: "Millions of unchanged rows are transported on every run, wasting bandwidth & storage." },
      { icon: iDB,    color: C.purple, title: "Source DB Strain",
        body: "Long full-SELECT queries lock transactional systems (SAP SQL Server, MySQL, Oracle)." },
      { icon: iLog,   color: C.snowBlue, title: "No Auditability",
        body: "Standard pipelines lack load timestamps, watermark tracking, and row-level metrics." },
    ];

    const cols = [0.4, 5.15];
    problems.forEach((p, i) => {
      const col = cols[i % 2];
      const row = i < 2 ? 1.2 : 3.05;
      // card
      card(s, col, row, 4.55, 1.65, C.offWhite);
      // icon circle
      s.addShape("OVAL", { x: col + 0.15, y: row + 0.2, w: 0.55, h: 0.55,
        fill: { color: p.color }, line: { color: p.color } });
      if (p.icon) s.addImage({ data: p.icon, x: col + 0.22, y: row + 0.26, w: 0.4, h: 0.4 });
      s.addText(p.title, { x: col + 0.85, y: row + 0.22, w: 3.55, h: 0.3,
        fontSize: 11, bold: true, color: C.darkBlue, margin: 0 });
      s.addText(p.body, { x: col + 0.85, y: row + 0.56, w: 3.55, h: 0.95,
        fontSize: 9.5, color: C.slate, margin: 0 });
    });

    // Objective bar
    s.addShape("RECTANGLE", { x: 0.4, y: 4.88, w: 9.2, h: 0.42,
      fill: { color: C.lightBlue }, line: { color: C.border } });
    s.addText("Objective: Extract only new/modified rows → stage incrementally via Parquet → merge into Snowflake", {
      x: 0.55, y: 4.88, w: 9.0, h: 0.42, fontSize: 10, bold: false,
      color: C.darkBlue, valign: "middle", margin: 0 });
  }

  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 3 — PIPELINE DESCRIPTION & OBJECTIVES
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    slideTitle(s, "Pipeline Description & Core Objectives");
    footer(s, 3, TOTAL);

    // Left: description box
    accentCard(s, 0.4, 1.15, 3.9, 1.8);
    s.addText("System Description", { x: 0.55, y: 1.2, w: 3.6, h: 0.3,
      fontSize: 10, bold: true, color: C.darkBlue, margin: 0 });
    s.addText(
      "A metadata-driven Python ingestion backend (with FastAPI control UI) that coordinates incremental extracts based on a Snowflake-persisted control table.",
      { x: 0.55, y: 1.55, w: 3.6, h: 1.3, fontSize: 9.5, color: C.slate, margin: 0 });

    // Right: 4 objectives
    const objs = [
      { icon: iCost,   color: C.green,   t: "Compute Savings",       b: "Atomic row-level merges — no table rebuilds" },
      { icon: iFile,   color: C.snowBlue, t: "Parquet Serialisation", b: "Snappy-compressed files reduce transfer time" },
      { icon: iGear,   color: C.purple,  t: "Metadata Driven",        b: "Schema, PKs & watermarks via config, not code" },
      { icon: iLock,   color: C.orange,  t: "Staging Cleanup",        b: "RAW truncation + cloud archive after each run" },
    ];
    objs.forEach((o, i) => {
      const x = 4.55, y = 1.15 + i * 0.98;
      card(s, x, y, 5.05, 0.85, C.offWhite);
      s.addShape("OVAL", { x: x + 0.1, y: y + 0.15, w: 0.5, h: 0.5,
        fill: { color: o.color }, line: { color: o.color } });
      if (o.icon) s.addImage({ data: o.icon, x: x + 0.16, y: y + 0.2, w: 0.38, h: 0.38 });
      s.addText(o.t, { x: x + 0.72, y: y + 0.1, w: 4.2, h: 0.28,
        fontSize: 10, bold: true, color: C.darkBlue, margin: 0 });
      s.addText(o.b, { x: x + 0.72, y: y + 0.4, w: 4.2, h: 0.35,
        fontSize: 9, color: C.slate, margin: 0 });
    });
  }

  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 4 — ARCHITECTURE DIAGRAM (PNG-based, fully reliable)
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    slideTitle(s, "High-Level Architecture", "Source → Python Engine → Cloud Storage → Snowflake");
    footer(s, 4, TOTAL);
    s.addImage({ path: "/home/claude/arch_highlevel.png", x: 0.22, y: 1.05, w: 9.56, h: 4.38 });
  }



  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 5 — SNOWFLAKE INTERNAL ARCHITECTURE (PNG-based)
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    slideTitle(s, "Snowflake Internal Architecture", "Virtual Warehouse · External Stages · RAW DB · Target DW");
    footer(s, 5, TOTAL);
    s.addImage({ path: "/home/claude/arch_snowflake.png", x: 0.22, y: 1.05, w: 9.56, h: 4.38 });
  }


  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 6 — END-TO-END DATA FLOW (PNG + key bullets)
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    slideTitle(s, "End-to-End Data Flow");
    footer(s, 6, TOTAL);

    // Data flow diagram PNG
    s.addImage({ path: "/home/claude/arch_dataflow.png", x: 0.22, y: 1.05, w: 9.56, h: 2.7 });

    // Key attributes below the diagram
    const attrs = [
      "Source data is read into Pandas and converted to Apache Arrow binary (Parquet)",
      "Cloud files staged with prefix: /database/schema/table/  (S3, Azure Blob, or GCS)",
      "COPY INTO RAW: MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE  ·  FORCE = TRUE",
      "MERGE is atomic — PK deduplication via ROW_NUMBER() window function",
    ];
    attrs.forEach((a, i) => {
      if (iCheck) s.addImage({ data: iCheck, x: 0.38, y: 3.95 + i * 0.38, w: 0.22, h: 0.22 });
      s.addText(a, { x: 0.66, y: 3.95 + i * 0.38, w: 9.1, h: 0.3,
        fontSize: 9.5, color: C.slate, margin: 0 });
    });
  }

  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 7 — PHASES 1–5
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    slideTitle(s, "Step-by-Step Workflow · Phases 1–5", "Extraction to cloud upload");
    footer(s, 7, TOTAL);

    const phases = [
      { n: "1", title: "Watermark Retrieval",    body: "Query PipelineRunControl for max watermark_value from last successful run.", color: C.purple },
      { n: "2", title: "Overlap Window Calc",    body: "Window Start = Watermark − 30 min  (accounts for slow transactions & clock drift).", color: C.orange },
      { n: "3", title: "Incremental Extract",    body: "Run dialect-specific SQL: SELECT … WHERE watermark_col > [Window Start].", color: C.snowBlue },
      { n: "4", title: "Schema Mapping",         body: "Apply user-defined column maps, constants, and default values on-the-fly.", color: C.green },
      { n: "5", title: "Upload & Clean Local",   body: "Write Snappy Parquet → upload to Cloud Stage → purge local /Extract folder.", color: C.red },
    ];

    phases.forEach((ph, i) => {
      const x = 0.38 + (i % 3) * 3.1;
      const y = i < 3 ? 1.15 : 3.05;
      const w = 2.85, h = 1.72;
      card(s, x, y, w, h, C.offWhite);
      // Colored top bar
      s.addShape("RECTANGLE", { x, y, w, h: 0.06, fill: { color: ph.color }, line: { color: ph.color } });
      // Phase number circle
      s.addShape("OVAL", { x: x + 0.1, y: y + 0.12, w: 0.44, h: 0.44,
        fill: { color: ph.color }, line: { color: ph.color } });
      s.addText(ph.n, { x: x + 0.1, y: y + 0.12, w: 0.44, h: 0.44,
        fontSize: 12, bold: true, color: C.white, align: "center", margin: 0 });
      s.addText("Phase " + ph.n, { x: x + 0.62, y: y + 0.12, w: 2.1, h: 0.24,
        fontSize: 8, color: C.lightSlate, margin: 0 });
      s.addText(ph.title, { x: x + 0.1, y: y + 0.62, w: w - 0.2, h: 0.3,
        fontSize: 10, bold: true, color: C.darkBlue, margin: 0 });
      s.addText(ph.body, { x: x + 0.1, y: y + 0.96, w: w - 0.2, h: 0.68,
        fontSize: 9, color: C.slate, margin: 0 });
    });
  }

  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 8 — PHASES 6–10
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    slideTitle(s, "Step-by-Step Workflow · Phases 6–10", "Load, merge, clean, log");
    footer(s, 8, TOTAL);

    const phases = [
      { n: "6", title: "RAW Table Verification",  body: "Dynamically CREATE staging table in <DB>_RAW.<SCHEMA>.<table> if not exists.", color: C.purple },
      { n: "7", title: "COPY INTO RAW",            body: "COPY INTO from External Stage · FORCE = TRUE · MATCH_BY_COLUMN_NAME.", color: C.orange },
      { n: "8", title: "Deduplicated MERGE",        body: "ROW_NUMBER() dedup on PKs · atomic WHEN MATCHED UPDATE / WHEN NOT MATCHED INSERT.", color: C.snowBlue },
      { n: "9", title: "Post-Load Cleanup",         body: "1. TRUNCATE RAW staging table.  2. Move Parquet files to /archive prefix.", color: C.green },
      { n:"10", title: "Control Table Logging",     body: "INSERT run metrics: rows inserted/updated, duration, watermark, status = SUCCESS/FAILED.", color: C.red },
    ];

    phases.forEach((ph, i) => {
      const x = 0.38 + (i % 3) * 3.1;
      const y = i < 3 ? 1.15 : 3.05;
      const w = 2.85, h = 1.72;
      card(s, x, y, w, h, C.offWhite);
      s.addShape("RECTANGLE", { x, y, w, h: 0.06, fill: { color: ph.color }, line: { color: ph.color } });
      s.addShape("OVAL", { x: x + 0.1, y: y + 0.12, w: 0.44, h: 0.44,
        fill: { color: ph.color }, line: { color: ph.color } });
      s.addText(ph.n, { x: x + 0.1, y: y + 0.12, w: 0.44, h: 0.44,
        fontSize: ph.n === "10" ? 10 : 12, bold: true, color: C.white, align: "center", margin: 0 });
      s.addText("Phase " + ph.n, { x: x + 0.62, y: y + 0.12, w: 2.1, h: 0.24,
        fontSize: 8, color: C.lightSlate, margin: 0 });
      s.addText(ph.title, { x: x + 0.1, y: y + 0.62, w: w - 0.2, h: 0.3,
        fontSize: 10, bold: true, color: C.darkBlue, margin: 0 });
      s.addText(ph.body, { x: x + 0.1, y: y + 0.96, w: w - 0.2, h: 0.68,
        fontSize: 9, color: C.slate, margin: 0 });
    });
  }

  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 9 — CONTROL TABLE DDL
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    slideTitle(s, "PipelineRunControl · DDL & Purpose", "The self-healing state machine");
    footer(s, 9, TOTAL);

    // Table header
    s.addShape("RECTANGLE", { x: 0.38, y: 1.15, w: 9.24, h: 0.35,
      fill: { color: C.darkBlue }, line: { color: C.darkBlue } });
    s.addText("Column", { x: 0.45, y: 1.15, w: 2.5, h: 0.35,
      fontSize: 9, bold: true, color: C.white, valign: "middle", margin: 0 });
    s.addText("Type", { x: 2.95, y: 1.15, w: 2.0, h: 0.35,
      fontSize: 9, bold: true, color: C.white, valign: "middle", margin: 0 });
    s.addText("Purpose", { x: 4.95, y: 1.15, w: 4.6, h: 0.35,
      fontSize: 9, bold: true, color: C.white, valign: "middle", margin: 0 });

    const rows = [
      ["run_id",           "VARCHAR (UUID)",    "Unique execution identifier"],
      ["source_system",    "VARCHAR",           "Source connection identity"],
      ["source_database",  "VARCHAR",           "Source DB name"],
      ["target_database",  "VARCHAR",           "Target Snowflake DB"],
      ["target_table",     "VARCHAR",           "Target table name"],
      ["source_row_count", "NUMBER",            "Rows read from source"],
      ["inserted_rows",    "NUMBER",            "Net new rows inserted"],
      ["updated_rows",     "NUMBER",            "Rows updated via MERGE"],
      ["status",           "VARCHAR",           "SUCCESS / FAILED"],
      ["watermark_value",  "TIMESTAMP_NTZ",     "High-watermark for next incremental pull"],
      ["run_start / end",  "TIMESTAMP_NTZ",     "Execution window timestamps"],
    ];

    rows.forEach((row, i) => {
      const ry = 1.5 + i * 0.33;
      const bg = i % 2 === 0 ? C.white : C.offWhite;
      s.addShape("RECTANGLE", { x: 0.38, y: ry, w: 9.24, h: 0.33,
        fill: { color: bg }, line: { color: C.border, width: 0.3 } });
      s.addText(row[0], { x: 0.45, y: ry, w: 2.45, h: 0.33,
        fontSize: 8.5, bold: true, color: C.snowBlue, fontFace: "Consolas", valign: "middle", margin: 0 });
      s.addText(row[1], { x: 2.95, y: ry, w: 1.95, h: 0.33,
        fontSize: 8, color: C.slate, fontFace: "Consolas", valign: "middle", margin: 0 });
      s.addText(row[2], { x: 4.95, y: ry, w: 4.6, h: 0.33,
        fontSize: 8.5, color: C.darkBlue, valign: "middle", margin: 0 });
    });

    // Footer callout
    s.addShape("RECTANGLE", { x: 0.38, y: 5.13, w: 9.24, h: 0.3,
      fill: { color: "EEF7FC" }, line: { color: C.border } });
    s.addText("Self-healing: each run reads its own last watermark → no manual state management required", {
      x: 0.5, y: 5.13, w: 9.1, h: 0.3, fontSize: 9, color: C.darkBlue,
      valign: "middle", margin: 0, italic: true });
  }

  // ════════════════════════════════════════════════════════════════════════════
  // SLIDE 10 — MERGE / DEDUP SQL
  // ════════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    slideTitle(s, "Deduplication & MERGE Logic", "Handling overlapping source windows");
    footer(s, 10, TOTAL);

    // Problem box
    accentCard(s, 0.38, 1.15, 4.4, 1.2, C.red);
    s.addText("The Staging Dilemma", { x: 0.55, y: 1.2, w: 4.1, h: 0.28,
      fontSize: 10, bold: true, color: C.darkBlue, margin: 0 });
    s.addText("Overlapping time windows mean the RAW staging table can contain multiple versions of the same PK row. A naive INSERT/UPDATE would duplicate or overwrite incorrectly.", {
      x: 0.55, y: 1.5, w: 4.1, h: 0.78, fontSize: 9, color: C.slate, margin: 0 });

    // Solution box
    accentCard(s, 5.0, 1.15, 4.6, 1.2, C.green);
    s.addText("The Solution", { x: 5.15, y: 1.2, w: 4.3, h: 0.28,
      fontSize: 10, bold: true, color: C.darkBlue, margin: 0 });
    s.addText("ROW_NUMBER() OVER (PARTITION BY <pks> ORDER BY <watermark_col> DESC) inside the MERGE source CTE — only the latest version of each PK reaches the target.", {
      x: 5.15, y: 1.5, w: 4.3, h: 0.78, fontSize: 9, color: C.slate, margin: 0 });

    // SQL block - light bg for LibreOffice compat
    s.addShape("RECTANGLE", { x: 0.38, y: 2.5, w: 9.24, h: 2.85,
      fill: { color: "F0F4F8" }, line: { color: "CBD5E0", width: 1 } });
    // Left accent
    s.addShape("RECTANGLE", { x: 0.38, y: 2.5, w: 0.07, h: 2.85,
      fill: { color: C.snowBlue }, line: { color: C.snowBlue } });

    const sqlLines = [
      "MERGE INTO TargetTable t",
      "USING (",
      "    SELECT * EXCEPT(rn) FROM (",
      "        SELECT *, ROW_NUMBER() OVER (PARTITION BY PK_ID",
      "            ORDER BY LAST_MODIFIED DESC) rn",
      "        FROM Staging_RAW",
      "    ) WHERE rn = 1",
      ") r ON t.PK_ID = r.PK_ID",
      "WHEN MATCHED THEN",
      "    UPDATE SET t.VAL = r.VAL, ...",
      "WHEN NOT MATCHED THEN",
      "    INSERT (PK_ID, VAL, ...) VALUES (r.PK_ID, r.VAL, ...);",
    ];

    const keyWords = ["MERGE INTO", "USING", "SELECT", "FROM", "WHERE", "ON", "WHEN MATCHED", "WHEN NOT MATCHED", "UPDATE SET", "INSERT", "ROW_NUMBER()", "PARTITION BY", "ORDER BY"];

    sqlLines.forEach((line, i) => {
      const isKw = keyWords.some(kw => line.trim().startsWith(kw));
      s.addText(line, { x: 0.6, y: 2.58 + i * 0.215, w: 8.9, h: 0.22,
        fontFace: "Consolas", fontSize: 9, bold: isKw,
        color: isKw ? "1A365D" : "2D3748", margin: 0 });
    });
  }

  // ════════════════════════════════════════════════════════════════════════════
  // Write file
  // ════════════════════════════════════════════════════════════════════════════
  const outPath = "/mnt/user-data/outputs/Snowflake_Incremental_Ingestion_Engine.pptx";
  await pres.writeFile({ fileName: outPath });
  console.log("✅ Written:", outPath);
}

buildPptx().catch(e => { console.error(e); process.exit(1); });