import React, { useState, useMemo } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LabelList,
} from "recharts";
import {
  LayoutGrid, TrendingUp, Filter as FunnelIcon, RotateCcw,
  Brain, FlaskConical,
} from "lucide-react";

// REAL data, exported directly from Postgres via export_all_by_year.py.
// query result against the project's 20,000-customer dataset.

const MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const monthlyGrowth = [
  { year: 2024, month: "Aug", customers: 398 }, { year: 2024, month: "Sep", customers: 799 },
  { year: 2024, month: "Oct", customers: 819 }, { year: 2024, month: "Nov", customers: 871 },
  { year: 2024, month: "Dec", customers: 879 },
  { year: 2025, month: "Jan", customers: 806 }, { year: 2025, month: "Feb", customers: 774 },
  { year: 2025, month: "Mar", customers: 818 }, { year: 2025, month: "Apr", customers: 800 },
  { year: 2025, month: "May", customers: 794 }, { year: 2025, month: "Jun", customers: 811 },
  { year: 2025, month: "Jul", customers: 873 }, { year: 2025, month: "Aug", customers: 861 },
  { year: 2025, month: "Sep", customers: 804 }, { year: 2025, month: "Oct", customers: 881 },
  { year: 2025, month: "Nov", customers: 847 }, { year: 2025, month: "Dec", customers: 876 },
  { year: 2026, month: "Jan", customers: 816 }, { year: 2026, month: "Feb", customers: 767 },
  { year: 2026, month: "Mar", customers: 851 }, { year: 2026, month: "Apr", customers: 836 },
  { year: 2026, month: "May", customers: 859 }, { year: 2026, month: "Jun", customers: 860 },
  { year: 2026, month: "Jul", customers: 811 }, { year: 2026, month: "Aug", customers: 489 },
];

const monthlySpend = [
  { year: 2024, month: "Aug", channel: "Google", spend: 1835.3 }, { year: 2024, month: "Aug", channel: "Meta", spend: 1195.51 },
  { year: 2024, month: "Sep", channel: "Google", spend: 4503.29 }, { year: 2024, month: "Sep", channel: "Meta", spend: 2893.44 },
  { year: 2024, month: "Oct", channel: "Google", spend: 5397.31 }, { year: 2024, month: "Oct", channel: "Meta", spend: 2551.45 },
  { year: 2024, month: "Nov", channel: "Google", spend: 5024.17 }, { year: 2024, month: "Nov", channel: "Meta", spend: 2266.59 },
  { year: 2024, month: "Dec", channel: "Google", spend: 5324.29 }, { year: 2024, month: "Dec", channel: "Meta", spend: 2899.53 },
  { year: 2025, month: "Jan", channel: "Google", spend: 5959.8 }, { year: 2025, month: "Jan", channel: "Meta", spend: 2775.15 },
  { year: 2025, month: "Feb", channel: "Google", spend: 4890.04 }, { year: 2025, month: "Feb", channel: "Meta", spend: 2609.66 },
  { year: 2025, month: "Mar", channel: "Google", spend: 5453.68 }, { year: 2025, month: "Mar", channel: "Meta", spend: 2492.06 },
  { year: 2025, month: "Apr", channel: "Google", spend: 4920.31 }, { year: 2025, month: "Apr", channel: "Meta", spend: 2502.07 },
  { year: 2025, month: "May", channel: "Google", spend: 4860.81 }, { year: 2025, month: "May", channel: "Meta", spend: 2509.13 },
  { year: 2025, month: "Jun", channel: "Google", spend: 4744.81 }, { year: 2025, month: "Jun", channel: "Meta", spend: 2826.37 },
  { year: 2025, month: "Jul", channel: "Google", spend: 4419.91 }, { year: 2025, month: "Jul", channel: "Meta", spend: 2530.83 },
  { year: 2025, month: "Aug", channel: "Google", spend: 5526.82 }, { year: 2025, month: "Aug", channel: "Meta", spend: 2973.18 },
  { year: 2025, month: "Sep", channel: "Google", spend: 4634.45 }, { year: 2025, month: "Sep", channel: "Meta", spend: 2595.07 },
  { year: 2025, month: "Oct", channel: "Google", spend: 5456.94 }, { year: 2025, month: "Oct", channel: "Meta", spend: 3040.64 },
  { year: 2025, month: "Nov", channel: "Google", spend: 4771.2 }, { year: 2025, month: "Nov", channel: "Meta", spend: 2594.53 },
  { year: 2025, month: "Dec", channel: "Google", spend: 5085.92 }, { year: 2025, month: "Dec", channel: "Meta", spend: 3108.86 },
  { year: 2026, month: "Jan", channel: "Google", spend: 5390.1 }, { year: 2026, month: "Jan", channel: "Meta", spend: 2620.31 },
  { year: 2026, month: "Feb", channel: "Google", spend: 4304.1 }, { year: 2026, month: "Feb", channel: "Meta", spend: 2380.56 },
  { year: 2026, month: "Mar", channel: "Google", spend: 5050.42 }, { year: 2026, month: "Mar", channel: "Meta", spend: 2759.83 },
  { year: 2026, month: "Apr", channel: "Google", spend: 5457.0 }, { year: 2026, month: "Apr", channel: "Meta", spend: 2689.82 },
  { year: 2026, month: "May", channel: "Google", spend: 5378.26 }, { year: 2026, month: "May", channel: "Meta", spend: 2687.14 },
  { year: 2026, month: "Jun", channel: "Google", spend: 5116.81 }, { year: 2026, month: "Jun", channel: "Meta", spend: 2649.71 },
  { year: 2026, month: "Jul", channel: "Google", spend: 5266.19 }, { year: 2026, month: "Jul", channel: "Meta", spend: 2396.64 },
  { year: 2026, month: "Aug", channel: "Google", spend: 3076.4 }, { year: 2026, month: "Aug", channel: "Meta", spend: 1377.48 },
];

const channelPerformanceByYear = [
  { year: 2024, channel: "Google", newCustomers: 1142, avgLtv: 356.35, spend: 22084.36, cac: 19.34, revenue: 74764.49, roas: 3.39, ltvCac: 18.43 },
  { year: 2024, channel: "Meta", newCustomers: 909, avgLtv: 328.04, spend: 11806.52, cac: 12.99, revenue: 64462.70, roas: 5.46, ltvCac: 25.26 },
  { year: 2025, channel: "Google", newCustomers: 2962, avgLtv: 249.41, spend: 60724.69, cac: 20.50, revenue: 155283.48, roas: 2.56, ltvCac: 12.17 },
  { year: 2025, channel: "Meta", newCustomers: 2530, avgLtv: 243.75, spend: 32557.55, cac: 12.87, revenue: 128359.81, roas: 3.94, ltvCac: 18.94 },
  { year: 2026, channel: "Google", newCustomers: 1861, avgLtv: 91.40, spend: 39039.28, cac: 20.98, revenue: 72328.96, roas: 1.85, ltvCac: 4.36 },
  { year: 2026, channel: "Meta", newCustomers: 1587, avgLtv: 82.21, spend: 19561.49, cac: 12.33, revenue: 51300.90, roas: 2.62, ltvCac: 6.67 },
];

const channelPerformanceAllTime = [
  { channel: "Google", newCustomers: 5965, avgLtv: 220.59, spend: 121848.33, cac: 20.43, revenue: 302376.93, roas: 2.48, ltvCac: 10.80 },
  { channel: "Meta", newCustomers: 5026, avgLtv: 207.99, spend: 63925.56, cac: 12.72, revenue: 244123.41, roas: 3.82, ltvCac: 16.35 },
];

const funnelByYear = [
  { year: 2024, stage: "Page View", value: 10520 }, { year: 2024, stage: "View Item", value: 5772 },
  { year: 2024, stage: "Add to Cart", value: 1784 }, { year: 2024, stage: "Begin Checkout", value: 978 },
  { year: 2024, stage: "Purchase", value: 625 },
  { year: 2025, stage: "Page View", value: 49266 }, { year: 2025, stage: "View Item", value: 27044 },
  { year: 2025, stage: "Add to Cart", value: 8175 }, { year: 2025, stage: "Begin Checkout", value: 4514 },
  { year: 2025, stage: "Purchase", value: 2959 },
  { year: 2026, stage: "Page View", value: 38420 }, { year: 2026, stage: "View Item", value: 21164 },
  { year: 2026, stage: "Add to Cart", value: 6345 }, { year: 2026, stage: "Begin Checkout", value: 3521 },
  { year: 2026, stage: "Purchase", value: 2273 },
];

const funnelAllTime = [
  { stage: "Page View", value: 98206 }, { stage: "View Item", value: 53980 },
  { stage: "Add to Cart", value: 16304 }, { stage: "Begin Checkout", value: 9013 },
  { stage: "Purchase", value: 5857 },
];

const retentionByYear = [
  { year: 2024, month: "Aug", rate: 80.3 }, { year: 2024, month: "Sep", rate: 61.2 },
  { year: 2024, month: "Oct", rate: 55.2 }, { year: 2024, month: "Nov", rate: 54.6 },
  { year: 2024, month: "Dec", rate: 52.5 },
  { year: 2025, month: "Jan", rate: 52.0 }, { year: 2025, month: "Feb", rate: 54.8 },
  { year: 2025, month: "Mar", rate: 53.2 }, { year: 2025, month: "Apr", rate: 52.0 },
  { year: 2025, month: "May", rate: 49.7 }, { year: 2025, month: "Jun", rate: 51.4 },
  { year: 2025, month: "Jul", rate: 50.1 }, { year: 2025, month: "Aug", rate: 49.0 },
  { year: 2025, month: "Sep", rate: 50.1 }, { year: 2025, month: "Oct", rate: 49.2 },
  { year: 2025, month: "Nov", rate: 50.2 }, { year: 2025, month: "Dec", rate: 46.8 },
  { year: 2026, month: "Jan", rate: 46.4 }, { year: 2026, month: "Feb", rate: 49.1 },
  { year: 2026, month: "Mar", rate: 45.3 }, { year: 2026, month: "Apr", rate: 46.0 },
  { year: 2026, month: "May", rate: 46.5 }, { year: 2026, month: "Jun", rate: 46.2 },
  { year: 2026, month: "Jul", rate: 30.5 }, { year: 2026, month: "Aug", rate: 0.0 },
];

const CHURN_BAND_ORDER = ["Low Risk", "Medium Risk", "High Risk"];
const churnRiskBandsByYear = [
  { year: 2024, band: "Low Risk", count: 1184, avgLtv: 485.93 },
  { year: 2025, band: "Low Risk", count: 1148, avgLtv: 387.28 },
  { year: 2025, band: "Medium Risk", count: 1701, avgLtv: 298.64 },
  { year: 2025, band: "High Risk", count: 181, avgLtv: 244.74 },
  { year: 2026, band: "Medium Risk", count: 1370, avgLtv: 94.90 },
  { year: 2026, band: "High Risk", count: 641, avgLtv: 124.21 },
];
// Note: 2024 has no Medium/High Risk rows because that cohort is old
// enough that essentially none remain at risk - a real reflection of
// the "risk drops sharply after ~12-17 months" finding from the churn model.

const PROPENSITY_BAND_ORDER = ["Low", "Medium", "High"];
const propensityBandsByYear = [
  { year: 2024, band: "Low", count: 685 }, { year: 2024, band: "Medium", count: 1293 }, { year: 2024, band: "High", count: 1788 },
  { year: 2025, band: "Low", count: 2377 }, { year: 2025, band: "Medium", count: 3724 }, { year: 2025, band: "High", count: 3844 },
  { year: 2026, band: "Low", count: 2389 }, { year: 2026, band: "Medium", count: 2647 }, { year: 2026, band: "High", count: 1253 },
];

// Only 2026 has A/B test data - the experiment was only run recently
// (assignments are scoped to the last 60 days of activity).
const abTestByYear = {
  2026: [{ variant: "A (Control)", rate: 24.11, assigned: 3484, converted: 840 }, { variant: "B (Redesign)", rate: 29.05, assigned: 3432, converted: 997 }],
};
const abTestAllTime = [
  { variant: "A (Control)", rate: 24.11, assigned: 3484, converted: 840 },
  { variant: "B (Redesign)", rate: 29.05, assigned: 3432, converted: 997 },
];

const COLORS = { teal: "#2dd4bf", pink: "#f472b6", blue: "#60a5fa", amber: "#fbbf24", muted: "#8896ab" };
const CHANNEL_COLORS = { Google: COLORS.blue, Meta: COLORS.pink };
const PIE_COLORS = [COLORS.teal, COLORS.amber, COLORS.pink, COLORS.blue];
const tooltipStyle = { backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "8px", fontSize: "12px", color: "#e2e8f0" };

const TABS = [
  { id: "overview", label: "Overview", icon: LayoutGrid },
  { id: "channel", label: "Channels", icon: TrendingUp },
  { id: "funnel", label: "Funnel & Retention", icon: FunnelIcon },
  { id: "ml", label: "ML Insights", icon: Brain },
  { id: "abtest", label: "A/B Test", icon: FlaskConical },
];

function Card({ title, sub, children }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5">
      {title && <h3 className="text-sm font-semibold text-slate-200">{title}</h3>}
      {sub && <p className="text-xs text-slate-500 mb-3">{sub}</p>}
      {!sub && title && <div className="mb-3" />}
      {children}
    </div>
  );
}

function KPI({ label, value, sub }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4">
      <p className="text-[11px] uppercase tracking-wide text-slate-400 font-semibold mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-50">{value}</p>
      {sub && <p className="text-xs text-teal-400 mt-1">{sub}</p>}
    </div>
  );
}

function EmptyState({ text }) {
  return <div className="text-sm text-slate-500 italic py-10 text-center">{text}</div>;
}

export default function MarketingDashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedYear, setSelectedYear] = useState("All");

  const years = useMemo(() => ["All", ...Array.from(new Set(monthlyGrowth.map((d) => d.year))).sort()], []);
  const isAll = selectedYear === "All";

  // ---- Overview ----
  const filteredGrowth = useMemo(() => {
    const rows = isAll ? monthlyGrowth : monthlyGrowth.filter((d) => d.year === selectedYear);
    const byMonth = {};
    rows.forEach((r) => { byMonth[r.month] = (byMonth[r.month] || 0) + r.customers; });
    return MONTH_ORDER.filter((m) => byMonth[m] !== undefined).map((m) => ({ month: m, customers: byMonth[m] }));
  }, [selectedYear]);

  const filteredSpend = useMemo(() => {
    const rows = isAll ? monthlySpend : monthlySpend.filter((d) => d.year === selectedYear);
    const byMonth = {};
    rows.forEach((r) => {
      if (!byMonth[r.month]) byMonth[r.month] = { month: r.month, Google: 0, Meta: 0 };
      byMonth[r.month][r.channel] += r.spend;
    });
    return MONTH_ORDER.filter((m) => byMonth[m] !== undefined).map((m) => byMonth[m]);
  }, [selectedYear]);

  const channelForPeriod = useMemo(
    () => (isAll ? channelPerformanceAllTime : channelPerformanceByYear.filter((c) => c.year === selectedYear)),
    [selectedYear]
  );

  const totalCustomersPeriod = filteredGrowth.reduce((s, d) => s + d.customers, 0);
  const totalLtvPeriod = channelForPeriod.reduce((s, c) => s + c.avgLtv * c.newCustomers, 0);
  const totalNewCustomersPeriod = channelForPeriod.reduce((s, c) => s + c.newCustomers, 0);
  const avgLtvPerCustomerPeriod = totalNewCustomersPeriod > 0 ? totalLtvPeriod / totalNewCustomersPeriod : 0;
  const bestLtvCac = channelForPeriod.length ? Math.max(...channelForPeriod.map((c) => c.ltvCac)) : 0;
  const bestLtvCacChannel = channelForPeriod.find((c) => c.ltvCac === bestLtvCac)?.channel || "—";

  //  Funnel & Retention 
  const filteredFunnel = useMemo(() => {
    const rows = isAll ? funnelAllTime : funnelByYear.filter((d) => d.year === selectedYear);
    if (!rows.length) return [];
    const initial = rows[0].value;
    return rows.map((r) => ({ ...r, pct: Math.round((r.value / initial) * 1000) / 10 }));
  }, [selectedYear]);

  const filteredRetention = useMemo(
    () => (isAll ? retentionByYear : retentionByYear.filter((d) => d.year === selectedYear)),
    [selectedYear]
  );

  //  ML Insights 
  const filteredChurnBands = useMemo(() => {
    const rows = isAll
      ? CHURN_BAND_ORDER.map((band) => {
          const matches = churnRiskBandsByYear.filter((d) => d.band === band);
          const count = matches.reduce((s, d) => s + d.count, 0);
          const avgLtv = count > 0 ? matches.reduce((s, d) => s + d.avgLtv * d.count, 0) / count : 0;
          return { band, count, avgLtv: Math.round(avgLtv * 100) / 100 };
        })
      : CHURN_BAND_ORDER.map((band) => {
          const found = churnRiskBandsByYear.find((d) => d.year === selectedYear && d.band === band);
          return { band, count: found?.count || 0, avgLtv: found?.avgLtv || 0 };
        });
    return rows.filter((r) => r.count > 0);
  }, [selectedYear]);

  const filteredPropensityBands = useMemo(() => {
    const rows = isAll
      ? PROPENSITY_BAND_ORDER.map((band) => ({
          band, count: propensityBandsByYear.filter((d) => d.band === band).reduce((s, d) => s + d.count, 0),
        }))
      : PROPENSITY_BAND_ORDER.map((band) => {
          const found = propensityBandsByYear.find((d) => d.year === selectedYear && d.band === band);
          return { band, count: found?.count || 0 };
        });
    return rows.filter((r) => r.count > 0);
  }, [selectedYear]);

  //  A/B Test 
  const filteredAbTest = isAll ? abTestAllTime : (abTestByYear[selectedYear] || []);

  return (
    <div className="min-h-full w-full bg-slate-900 text-slate-100 p-6 font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="relative pl-4">
          <div className="absolute left-0 top-0 bottom-0 w-1 rounded bg-gradient-to-b from-teal-400 to-pink-400" />
          <h1 className="text-xl font-bold text-white">Marketing Intelligence Dashboard</h1>
          <p className="text-xs text-slate-400 mt-0.5">Channel performance · Funnel & retention · ML-driven insights · A/B testing — real data, filterable by year</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-400 font-medium">Year</label>
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value === "All" ? "All" : Number(e.target.value))}
            className="bg-slate-800 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-teal-400"
          >
            {years.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
          {!isAll && (
            <button onClick={() => setSelectedYear("All")} className="flex items-center gap-1 text-xs text-slate-400 hover:text-teal-400 transition">
              <RotateCcw size={12} /> Reset
            </button>
          )}
        </div>
      </div>

      <div className="flex gap-1 mb-6 border-b border-slate-800 overflow-x-auto">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-1.5 px-3.5 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition ${
                active ? "border-teal-400 text-teal-400" : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Icon size={15} /> {t.label}
            </button>
          );
        })}
      </div>

      {/* OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KPI label="Customers" value={totalCustomersPeriod.toLocaleString()} sub={isAll ? "All years" : `${selectedYear} only`} />
            <KPI label="Total LTV" value={`$${Math.round(totalLtvPeriod).toLocaleString()}`} sub={isAll ? "All years" : `${selectedYear} cohort, to-date`} />
            <KPI label="Avg LTV / Customer" value={`$${avgLtvPerCustomerPeriod.toFixed(2)}`} sub={isAll ? "All years" : `${selectedYear} cohort`} />
            <KPI label="Best LTV:CAC" value={`${bestLtvCac.toFixed(2)}x`} sub={`${bestLtvCacChannel} · ${isAll ? "All years" : selectedYear}`} />
          </div>

          <Card title={`New Customers by Month ${isAll ? "(All Years, Summed)" : `— ${selectedYear}`}`}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={filteredGrowth} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#243044" vertical={false} />
                <XAxis dataKey="month" stroke={COLORS.muted} fontSize={12} />
                <YAxis stroke={COLORS.muted} fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "#e2e8f0" }} />
                <Bar dataKey="customers" fill={COLORS.teal} radius={[4, 4, 0, 0]}>
                  <LabelList dataKey="customers" position="top" fill="#e2e8f0" fontSize={10} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title={`Spend by Channel, by Month ${isAll ? "(All Years, Summed)" : `— ${selectedYear}`}`}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={filteredSpend} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#243044" vertical={false} />
                <XAxis dataKey="month" stroke={COLORS.muted} fontSize={12} />
                <YAxis stroke={COLORS.muted} fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "#e2e8f0" }} formatter={(v) => `$${v.toFixed(0)}`} />
                <Legend wrapperStyle={{ fontSize: 12 }} formatter={(value) => <span style={{ color: "#e2e8f0" }}>{value}</span>} />
                <Bar dataKey="Google" fill={CHANNEL_COLORS.Google} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Meta" fill={CHANNEL_COLORS.Meta} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* CHANNEL PERFORMANCE */}
      {activeTab === "channel" && (
        <div className="space-y-5">
          <p className="text-xs text-slate-400 -mt-1">
            {isAll ? "All-time totals across every signup cohort." : `Cohort economics for customers who signed up in ${selectedYear}, measured to-date.`}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {channelForPeriod.map((c) => (
              <Card key={c.channel} title={c.channel}>
                <div className="grid grid-cols-2 gap-3">
                  <div><p className="text-[11px] text-slate-400">CAC</p><p className="text-lg font-bold">${c.cac}</p></div>
                  <div><p className="text-[11px] text-slate-400">ROAS</p><p className="text-lg font-bold">{c.roas}x</p></div>
                  <div><p className="text-[11px] text-slate-400">Avg LTV</p><p className="text-lg font-bold">${c.avgLtv}</p></div>
                  <div><p className="text-[11px] text-slate-400">LTV:CAC</p><p className="text-lg font-bold text-teal-400">{c.ltvCac}x</p></div>
                  <div><p className="text-[11px] text-slate-400">New Customers</p><p className="text-sm font-semibold">{c.newCustomers.toLocaleString()}</p></div>
                  <div><p className="text-[11px] text-slate-400">Total Spend</p><p className="text-sm font-semibold">${c.spend.toLocaleString()}</p></div>
                </div>
              </Card>
            ))}
          </div>
          <Card title="LTV : CAC Ratio by Channel">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={channelForPeriod} layout="vertical" margin={{ left: 10, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#243044" horizontal={false} />
                <XAxis type="number" stroke={COLORS.muted} fontSize={12} />
                <YAxis type="category" dataKey="channel" stroke={COLORS.muted} fontSize={12} width={60} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="ltvCac" radius={[0, 4, 4, 0]}>
                  {channelForPeriod.map((c) => <Cell key={c.channel} fill={CHANNEL_COLORS[c.channel]} />)}
                  <LabelList dataKey="ltvCac" position="right" fill="#e2e8f0" fontSize={12} formatter={(v) => `${v}x`} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {!isAll && selectedYear === 2026 && (
              <p className="text-xs text-amber-400 mt-3">
                Note: the {selectedYear} cohort's LTV:CAC is much lower than 2024/2025 — expected, since these customers
                have only had a few months to accumulate lifetime value. This is a cohort-maturity effect, not underperformance.
              </p>
            )}
          </Card>
        </div>
      )}

      {/* FUNNEL & RETENTION */}
      {activeTab === "funnel" && (
        <div className="space-y-5">
          <Card title={`Conversion Funnel ${isAll ? "(All-Time)" : `— ${selectedYear}`}`}>
            {filteredFunnel.length === 0 ? <EmptyState text="No funnel data for this year." /> : (
              <div className="space-y-2">
                {filteredFunnel.map((f, i) => (
                  <div key={f.stage} className="flex items-center gap-3">
                    <span className="text-xs text-slate-400 w-28 shrink-0">{f.stage}</span>
                    <div className="flex-1 bg-slate-800 rounded-full h-6 overflow-hidden">
                      <div
                        className="h-full rounded-full flex items-center justify-end pr-2 text-[11px] font-medium text-slate-900"
                        style={{ width: `${f.pct}%`, backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                      >
                        {f.pct}%
                      </div>
                    </div>
                    <span className="text-xs text-slate-400 w-16 text-right shrink-0">{f.value.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>
          <Card title={`Month-over-Month Retention ${isAll ? "(Full History)" : `— ${selectedYear}`}`}>
            {filteredRetention.length === 0 ? <EmptyState text="No retention data for this year." /> : (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={filteredRetention}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#243044" vertical={false} />
                  <XAxis dataKey="month" stroke={COLORS.muted} fontSize={12} />
                  <YAxis stroke={COLORS.muted} fontSize={12} domain={[0, 90]} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Line type="monotone" dataKey="rate" stroke={COLORS.teal} strokeWidth={2.5} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
            {!isAll && selectedYear === 2026 && (
              <p className="text-xs text-amber-400 mt-2">
                August 2026's 0% reflects the data cutoff — there's no "next month" yet to measure retention into.
              </p>
            )}
          </Card>
        </div>
      )}

      {/* ML INSIGHTS */}
      {activeTab === "ml" && (
        <div className="space-y-5">
          <p className="text-xs text-slate-400 -mt-1">Segmented by each customer's signup year.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Card title={`Churn Risk Bands ${isAll ? "(All Years)" : `— ${selectedYear}`}`}>
              {filteredChurnBands.length === 0 ? <EmptyState text="No churn scores for this year." /> : (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={filteredChurnBands} dataKey="count" nameKey="band"
                      innerRadius={50} outerRadius={80} paddingAngle={3}
                      label={({ band, percent }) => `${band}: ${(percent * 100).toFixed(0)}%`}
                      labelLine={{ stroke: COLORS.muted }}
                    >
                      {filteredChurnBands.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend wrapperStyle={{ fontSize: 11 }} formatter={(value) => <span style={{ color: "#e2e8f0" }}>{value}</span>} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Card>
            <Card title={`Purchase Propensity Bands ${isAll ? "(All Years)" : `— ${selectedYear}`}`}>
              {filteredPropensityBands.length === 0 ? <EmptyState text="No propensity scores for this year." /> : (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={filteredPropensityBands} dataKey="count" nameKey="band"
                      innerRadius={50} outerRadius={80} paddingAngle={3}
                      label={({ band, percent }) => `${band}: ${(percent * 100).toFixed(0)}%`}
                      labelLine={{ stroke: COLORS.muted }}
                    >
                      {filteredPropensityBands.map((_, i) => <Cell key={i} fill={PIE_COLORS[(i + 1) % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend wrapperStyle={{ fontSize: 11 }} formatter={(value) => <span style={{ color: "#e2e8f0" }}>{value}</span>} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>
          {!isAll && selectedYear === 2024 && (
            <p className="text-xs text-amber-400">
              The 2024 cohort shows almost no Medium/High risk customers left — a real reflection of the churn model's
              core finding: risk drops sharply once a customer passes ~12–17 months of tenure.
            </p>
          )}
          <Card title="Validated Model Findings (Methodology, Not Year-Specific)">
            <ul className="text-sm text-slate-300 space-y-2 list-disc list-inside">
              <li><span className="text-teal-400 font-medium">Churn:</span> tenure is the only strong, validated driver — confirmed via permutation importance and partial dependence, not just raw coefficients.</li>
              <li><span className="text-teal-400 font-medium">Purchase propensity:</span> browsing intent (product views) overwhelmingly dominates every other signal.</li>
              <li><span className="text-teal-400 font-medium">LTV model:</span> explains ~24% of variance (R²) — useful for ranking, not precise forecasting.</li>
            </ul>
          </Card>
        </div>
      )}

      {/* A/B TEST */}
      {activeTab === "abtest" && (
        <div className="space-y-5">
          {filteredAbTest.length === 0 ? (
            <Card>
              <EmptyState text={`No A/B test assignments exist for ${selectedYear} — the checkout redesign experiment only ran in 2026.`} />
            </Card>
          ) : (
            <>
              <Card title={`Checkout Redesign — Conversion Rate by Variant ${isAll ? "" : `(${selectedYear})`}`}>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={filteredAbTest} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#243044" vertical={false} />
                    <XAxis dataKey="variant" stroke={COLORS.muted} fontSize={12} />
                    <YAxis stroke={COLORS.muted} fontSize={12} unit="%" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
                      <Cell fill={COLORS.muted} />
                      <Cell fill={COLORS.teal} />
                      <LabelList dataKey="rate" position="top" fill="#e2e8f0" fontSize={12} formatter={(v) => `${v}%`} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>
              <Card>
                <p className="text-sm text-slate-300">
                  A two-proportion z-test confirmed a <span className="text-teal-400 font-semibold">+4.94pt lift</span> is
                  statistically significant (<span className="font-mono">p = 0.000003</span>, well below the 0.05 threshold).
                  Recommend rolling the redesign out to 100% of traffic.
                </p>
              </Card>
            </>
          )}
        </div>
      )}

      <div className="text-center text-xs text-slate-500 mt-10 pt-4 border-t border-slate-800">
        Marketing Intelligence Dashboard · Built by <span className="text-slate-300 font-medium">Temi Priscilla Jokotola</span>
      </div>
    </div>
  );
}
