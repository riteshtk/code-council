"use client";

import { useState, useEffect } from "react";
import { useConfigStore } from "@/stores/configStore";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Settings,
  Cpu,
  Users,
  FolderOpen,
  FileOutput,
  ChevronDown,
  ChevronUp,
  Check,
  Zap,
  Globe,
  Server,
  MonitorSpeaker,
  Brain,
  Plus,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { testProvider, createAgent, deleteAgent, listAgents } from "@/lib/api";
import { AGENTS, AGENT_HANDLES } from "@/lib/constants";


const PROVIDER_META: Record<string, { icon: React.ComponentType<{ className?: string }>; placeholder: string }> = {
  openai:    { icon: Zap,            placeholder: "sk-..." },
  anthropic: { icon: Brain,          placeholder: "sk-ant-..." },
  gemini:    { icon: Globe,          placeholder: "AIza..." },
  mistral:   { icon: Server,         placeholder: "..." },
  ollama:    { icon: MonitorSpeaker, placeholder: "N/A (local)" },
};

const FOCUS_AREAS = [
  "Security Surface", "Coupling Analysis", "CVE Scan", "Test Coverage",
  "API Contracts", "Performance", "Hidden Deps", "Blast Radius",
];

/* --- Agent card --- */
function AgentCard({ handle, agentCfg, onUpdate }: {
  handle: string;
  agentCfg: Record<string, unknown>;
  onUpdate: (patch: Record<string, unknown>) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const agentConst = AGENTS[handle as keyof typeof AGENTS];
  const meta = agentConst
    ? { label: agentConst.name, abbr: agentConst.abbr, role: agentConst.role, color: agentConst.color, icon: agentConst.icon }
    : { label: handle, abbr: "??", role: handle, color: "var(--cc-accent)", icon: Zap };
  const enabled = agentCfg?.enabled !== false;
  const provider = (agentCfg?.provider as string) || "default";
  const model = (agentCfg?.model as string) || "";
  const temperature = (agentCfg?.temperature as number) ?? 0.3;
  const maxTokens = (agentCfg?.max_tokens as number) ?? 2000;
  const voteWeight = (agentCfg?.vote_weight as number) ?? 1.0;
  const persona = (agentCfg?.persona as string) || "Default";
  const personaPrompt = (agentCfg?.persona_prompt as string) || "";
  const focusAreas = (agentCfg?.focus_areas as string[]) || FOCUS_AREAS;

  return (
    <div className="bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-xl overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 border-b border-[var(--cc-border)] cursor-pointer hover:bg-[var(--cc-bg-hover)] transition-colors duration-200"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold text-white shrink-0"
            style={{ backgroundColor: meta.color }}
          >
            {meta.abbr}
          </div>
          <div>
            <div className="text-[15px] font-semibold text-[var(--cc-text)]">{meta.label}</div>
            <div className="text-xs text-[var(--cc-text-muted)]">
              {meta.role}
              {!expanded && ` \u00b7 ${provider} ${model || ""} \u00b7 temp ${temperature}`}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={(e) => { e.stopPropagation(); onUpdate({ enabled: !enabled }); }}
            className={cn(
              "relative inline-flex h-6 w-11 items-center rounded-full cursor-pointer transition-colors duration-200",
              enabled ? "bg-[var(--cc-green)]" : "bg-[var(--cc-border)]"
            )}
          >
            <span className={cn(
              "inline-block h-5 w-5 rounded-full bg-white transition-transform duration-200",
              enabled ? "translate-x-[22px]" : "translate-x-0.5"
            )} />
          </button>
          {expanded
            ? <ChevronUp className="w-4 h-4 text-[var(--cc-text-muted)]" />
            : <ChevronDown className="w-4 h-4 text-[var(--cc-text-muted)]" />
          }
        </div>
      </div>

      {/* Expanded body */}
      {expanded && (
        <div className="p-5 grid grid-cols-2 gap-4 animate-fade-in">
          <FieldGroup label="Provider">
            <select
              value={provider}
              onChange={(e) => onUpdate({ provider: e.target.value })}
              className="w-full py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none cursor-pointer focus:border-[var(--cc-accent)]"
            >
              <option value="default">Default (OpenAI)</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Google</option>
              <option value="mistral">Mistral</option>
              <option value="ollama">Ollama</option>
            </select>
          </FieldGroup>

          <FieldGroup label="Model">
            <select
              value={model}
              onChange={(e) => onUpdate({ model: e.target.value })}
              className="w-full py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none cursor-pointer focus:border-[var(--cc-accent)]"
            >
              <option value="gpt-4o">gpt-4o</option>
              <option value="gpt-4o-mini">gpt-4o-mini</option>
              <option value="gpt-4-turbo">gpt-4-turbo</option>
              <option value="claude-sonnet">claude-sonnet</option>
            </select>
          </FieldGroup>

          <FieldGroup label="Temperature">
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={0}
                max={100}
                value={temperature * 100}
                onChange={(e) => onUpdate({ temperature: Number(e.target.value) / 100 })}
                className="flex-1 accent-[var(--cc-accent)] cursor-pointer"
              />
              <span className="text-[13px] font-mono text-[var(--cc-accent)] min-w-[36px]">{temperature.toFixed(1)}</span>
            </div>
          </FieldGroup>

          <FieldGroup label="Max Tokens">
            <input
              type="number"
              value={maxTokens}
              onChange={(e) => onUpdate({ max_tokens: Number(e.target.value) })}
              className="w-full py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none focus:border-[var(--cc-accent)]"
            />
          </FieldGroup>

          <FieldGroup label="Vote Weight">
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={0}
                max={200}
                value={voteWeight * 100}
                onChange={(e) => onUpdate({ vote_weight: Number(e.target.value) / 100 })}
                className="flex-1 accent-[var(--cc-accent)] cursor-pointer"
              />
              <span className="text-[13px] font-mono text-[var(--cc-accent)] min-w-[36px]">{voteWeight.toFixed(1)}</span>
            </div>
          </FieldGroup>

          <FieldGroup label="Persona">
            <select
              value={persona}
              onChange={(e) => onUpdate({ persona: e.target.value })}
              className="w-full py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none cursor-pointer focus:border-[var(--cc-accent)]"
            >
              <option value="Default">Default</option>
              <option value="Custom">Custom...</option>
            </select>
          </FieldGroup>

          {/* Focus Areas - full width */}
          <div className="col-span-2">
            <span className="text-[11px] font-semibold uppercase text-[var(--cc-text-muted)] tracking-wider">Focus Areas</span>
            <div className="flex flex-wrap gap-2 mt-2">
              {FOCUS_AREAS.map((area) => {
                const active = focusAreas.includes(area);
                return (
                  <button
                    key={area}
                    onClick={() => {
                      const updated = active
                        ? focusAreas.filter((a) => a !== area)
                        : [...focusAreas, area];
                      onUpdate({ focus_areas: updated });
                    }}
                    className={cn(
                      "py-1.5 px-3 rounded-md text-xs font-medium border cursor-pointer transition-all duration-200",
                      active
                        ? "bg-[var(--cc-accent-muted)] border-[var(--cc-accent)] text-[var(--cc-accent)]"
                        : "bg-[var(--cc-bg)] border-[var(--cc-border)] text-[var(--cc-text-muted)]"
                    )}
                  >
                    {area}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Persona Prompt - full width */}
          <div className="col-span-2">
            <span className="text-[11px] font-semibold uppercase text-[var(--cc-text-muted)] tracking-wider">Persona Prompt</span>
            <textarea
              value={personaPrompt}
              onChange={(e) => onUpdate({ persona_prompt: e.target.value })}
              className="w-full mt-2 min-h-[80px] p-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-lg text-xs font-mono leading-relaxed text-[var(--cc-text)] resize-y outline-none focus:border-[var(--cc-accent)] transition-all duration-200"
              placeholder="Custom persona prompt..."
            />
          </div>
        </div>
      )}
    </div>
  );
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[11px] font-semibold uppercase text-[var(--cc-text-muted)] tracking-wider">{label}</span>
      {children}
    </div>
  );
}

/* --- Main page --- */
export default function ConfigPage() {
  const { config, loading, loadConfig, updateConfig } = useConfigStore();
  const [dirty, setDirty] = useState(false);
  const [localConfig, setLocalConfig] = useState(config);
  const [saving, setSaving] = useState(false);
  const [nextRunOnly, setNextRunOnly] = useState(false);
  const [showAgentForm, setShowAgentForm] = useState(false);
  const [customAgents, setCustomAgents] = useState<Record<string, unknown>[]>([]);
  const [newAgent, setNewAgent] = useState({
    handle: "",
    name: "",
    role: "",
    color: "#ff9f43",
    persona_prompt: "",
    focus_areas: "",
    debate_role: "analyst",
    temperature: 0.3,
    vote_weight: 1.0,
  });

  useEffect(() => { loadConfig(); loadCustomAgents(); }, []);
  useEffect(() => { setLocalConfig(config); }, [config]);

  async function loadCustomAgents() {
    try {
      const agents = (await listAgents()) as unknown as Record<string, unknown>[];
      setCustomAgents(agents.filter((a) => a.is_custom));
    } catch {
      // ignore
    }
  }

  async function handleCreateAgent() {
    if (!newAgent.handle.trim() || !newAgent.name.trim()) {
      toast.error("Handle and Name are required");
      return;
    }
    try {
      await createAgent({
        ...newAgent,
        focus_areas: newAgent.focus_areas
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      toast.success(`Agent "${newAgent.name}" created`);
      setShowAgentForm(false);
      setNewAgent({
        handle: "",
        name: "",
        role: "",
        color: "#ff9f43",
        persona_prompt: "",
        focus_areas: "",
        debate_role: "analyst",
        temperature: 0.3,
        vote_weight: 1.0,
      });
      loadCustomAgents();
    } catch (e) {
      toast.error(`Failed to create agent: ${e}`);
    }
  }

  async function handleDeleteAgent(handle: string) {
    try {
      await deleteAgent(handle);
      toast.success("Agent deleted");
      loadCustomAgents();
    } catch (e) {
      toast.error(`Failed to delete agent: ${e}`);
    }
  }

  const lc = (localConfig ?? {}) as Record<string, unknown>;
  const council = (lc.council ?? {}) as Record<string, unknown>;
  const llm = (lc.llm ?? {}) as Record<string, unknown>;
  const providers = ((llm.providers ?? lc.providers ?? {}) as Record<string, Record<string, unknown>>);
  const agents = (lc.agents ?? {}) as Record<string, unknown>;
  const ingest = (lc.ingest ?? lc.ingestion ?? {}) as Record<string, unknown>;

  function patch(updates: Record<string, unknown>) {
    setLocalConfig((prev) => (prev ? { ...prev, ...updates } : prev));
    setDirty(true);
  }

  function patchCouncil(updates: Record<string, unknown>) {
    patch({ council: { ...council, ...updates } });
  }

  async function handleSave() {
    if (!localConfig) return;
    setSaving(true);
    try {
      await updateConfig(localConfig);
      setDirty(false);
      toast.success("Configuration saved");
    } catch {
      toast.error("Failed to save configuration");
    } finally {
      setSaving(false);
    }
  }

  if (loading && !config) {
    return (
      <div className="flex-1 px-8 lg:px-12 py-8 w-full space-y-4">
        <Skeleton className="h-8 w-48 rounded-lg" />
        <Skeleton className="h-12 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="flex-1 px-8 lg:px-12 py-8 animate-fade-in">
      {/* Header with save */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-[var(--cc-text)]">Configuration</h1>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-[var(--cc-text-muted)] cursor-pointer">
            <input
              type="checkbox"
              checked={nextRunOnly}
              onChange={(e) => setNextRunOnly(e.target.checked)}
              className="accent-[var(--cc-accent)]"
            />
            Apply only to next run
          </label>
          <button
            onClick={handleSave}
            disabled={saving}
            className="py-2 px-5 bg-[var(--cc-accent)] rounded-lg text-white text-[13px] font-semibold cursor-pointer hover:bg-[#5a4bd4] transition-colors duration-200 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Configuration"}
          </button>
        </div>
      </div>

      <Tabs defaultValue="agents">
        <TabsList className="mb-6">
          {[
            { value: "general", label: "General", icon: Settings },
            { value: "providers", label: "Providers", icon: Cpu },
            { value: "agents", label: "Agents", icon: Users },
            { value: "ingestion", label: "Ingestion", icon: FolderOpen },
            { value: "output", label: "Output", icon: FileOutput },
          ].map(({ value, label, icon: Icon }) => (
            <TabsTrigger key={value} value={value} className="flex items-center gap-1.5 cursor-pointer">
              <Icon className="w-3.5 h-3.5" />
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* General */}
        <TabsContent value="general">
          <div className="card-premium p-6 space-y-6">
            <h2 className="text-base font-semibold text-[var(--cc-text)]">Debate Settings</h2>
            <div className="grid grid-cols-2 gap-4">
              <FieldGroup label="Topology">
                <Select
                  value={(council.debate_topology as string) || "adversarial"}
                  onValueChange={(v) => v && patchCouncil({ debate_topology: v })}
                >
                  <SelectTrigger className="rounded-lg cursor-pointer">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["adversarial", "collaborative", "socratic", "open_floor", "panel", "custom"].map((t) => (
                      <SelectItem key={t} value={t} className="cursor-pointer capitalize">
                        {t.replace("_", " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FieldGroup>

              <FieldGroup label={`Debate Rounds: ${(council.max_rounds as number) || 3}`}>
                <input
                  type="range" min={1} max={10}
                  value={(council.max_rounds as number) || 3}
                  onChange={(e) => patchCouncil({ max_rounds: Number(e.target.value) })}
                  className="w-full accent-[var(--cc-accent)] cursor-pointer mt-1"
                />
              </FieldGroup>

              <FieldGroup label="Budget Limit ($)">
                <Input
                  type="number" min="0" step="1"
                  value={(council.budget_limit_usd as number) || ""}
                  onChange={(e) => patchCouncil({ budget_limit_usd: e.target.value ? parseFloat(e.target.value) : 0 })}
                  placeholder="No limit"
                  className="rounded-lg"
                />
              </FieldGroup>

              <FieldGroup label="Human-in-the-loop">
                <div className="mt-1 flex items-center gap-3">
                  <button
                    onClick={() => patchCouncil({ hitl_enabled: !council.hitl_enabled })}
                    className={cn(
                      "relative inline-flex h-6 w-11 items-center rounded-full cursor-pointer transition-colors duration-200",
                      council.hitl_enabled ? "bg-[var(--cc-accent)]" : "bg-[var(--cc-bg-active)]"
                    )}
                  >
                    <span className={cn(
                      "inline-block h-4 w-4 rounded-full bg-white transition-transform duration-200",
                      council.hitl_enabled ? "translate-x-6" : "translate-x-1"
                    )} />
                  </button>
                  <span className="text-sm text-[var(--cc-text-secondary)]">
                    {council.hitl_enabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
              </FieldGroup>
            </div>
          </div>
        </TabsContent>

        {/* Providers */}
        <TabsContent value="providers">
          <div className="flex flex-col gap-3">
            {Object.entries(PROVIDER_META).map(([name, meta]) => {
              const conf = providers[name] || {};
              const Icon = meta.icon;
              const hasKey = !!(conf.api_key as string);
              return (
                <div key={name} className="bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-[10px] px-5 py-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2 text-[15px] font-semibold text-[var(--cc-text)] capitalize">
                      <span className={cn("w-2 h-2 rounded-full", hasKey ? "bg-[var(--cc-green)]" : "bg-[var(--cc-red)]")} />
                      {name}
                    </div>
                    <span className="text-xs text-[var(--cc-text-muted)]">
                      {hasKey ? "Connected" : "Not configured"}
                    </span>
                  </div>
                  <div className="grid grid-cols-[1fr_1fr_auto] gap-3 items-end">
                    <FieldGroup label="API Key">
                      <Input
                        type="password"
                        value={(conf.api_key as string) || ""}
                        onChange={(e) => patch({
                          llm: { ...llm, providers: { ...providers, [name]: { ...conf, api_key: e.target.value } } }
                        })}
                        placeholder={meta.placeholder}
                        className="h-9 text-xs rounded-md"
                      />
                    </FieldGroup>
                    <FieldGroup label="Model">
                      <Input
                        value={(conf.model as string) || ""}
                        onChange={(e) => patch({
                          llm: { ...llm, providers: { ...providers, [name]: { ...conf, model: e.target.value } } }
                        })}
                        placeholder="Default model"
                        className="h-9 text-xs rounded-md"
                      />
                    </FieldGroup>
                    <button
                      onClick={async () => {
                        try {
                          await testProvider(name);
                          toast.success(`${name} provider connected successfully`);
                        } catch (e) {
                          toast.error(`${name} test failed: ${e}`);
                        }
                      }}
                      className="py-2 px-4 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-xs text-[var(--cc-text-muted)] font-semibold cursor-pointer hover:border-[var(--cc-accent)] hover:text-[var(--cc-text)] transition-all duration-200 h-9"
                    >
                      Test
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </TabsContent>

        {/* Agents */}
        <TabsContent value="agents">
          <div className="flex flex-col gap-4">
            {AGENT_HANDLES.map((handle) => {
              const agentCfg = (agents[handle] ?? {}) as Record<string, unknown>;
              return (
                <AgentCard
                  key={handle}
                  handle={handle}
                  agentCfg={agentCfg}
                  onUpdate={(agentPatch) => {
                    patch({ agents: { ...agents, [handle]: { ...agentCfg, ...agentPatch } } });
                  }}
                />
              );
            })}

            {/* Custom Agents */}
            {customAgents.length > 0 && (
              <div className="mt-4 pt-4 border-t border-[var(--cc-border)]">
                <h3 className="text-sm font-semibold text-[var(--cc-text)] mb-3">Custom Agents</h3>
                <div className="flex flex-col gap-3">
                  {customAgents.map((agent) => (
                    <div
                      key={agent.handle as string}
                      className="flex items-center justify-between px-5 py-4 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-xl"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold text-white shrink-0"
                          style={{ backgroundColor: (agent.color as string) || "#ff9f43" }}
                        >
                          {((agent.name as string) || "??").slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-[15px] font-semibold text-[var(--cc-text)]">{agent.name as string}</div>
                          <div className="text-xs text-[var(--cc-text-muted)]">
                            {agent.role as string} &middot; {agent.debate_role as string} &middot; temp {(agent.temperature as number)?.toFixed(1) ?? "0.3"}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteAgent(agent.handle as string)}
                        className="p-2 rounded-md text-[var(--cc-text-muted)] hover:text-[var(--cc-red)] hover:bg-[var(--cc-red-muted)] cursor-pointer transition-all duration-200"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Create Custom Agent */}
            <div className="mt-6 pt-6 border-t border-[var(--cc-border)]">
              <h3 className="text-sm font-semibold text-[var(--cc-text)] mb-4 flex items-center gap-2">
                <Plus className="w-4 h-4 text-[var(--cc-accent)]" />
                Create Custom Agent
              </h3>

              {showAgentForm ? (
                <div className="card-premium p-5 space-y-4 animate-fade-in">
                  <div className="grid grid-cols-2 gap-4">
                    <FieldGroup label="Handle (unique ID)">
                      <input
                        value={newAgent.handle}
                        onChange={(e) => setNewAgent({ ...newAgent, handle: e.target.value.toLowerCase().replace(/\s/g, "-") })}
                        placeholder="e.g. pragmatist"
                        className="w-full py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none focus:border-[var(--cc-accent)]"
                      />
                    </FieldGroup>
                    <FieldGroup label="Display Name">
                      <input
                        value={newAgent.name}
                        onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                        placeholder="e.g. The Pragmatist"
                        className="w-full py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none focus:border-[var(--cc-accent)]"
                      />
                    </FieldGroup>
                    <FieldGroup label="Role">
                      <input
                        value={newAgent.role}
                        onChange={(e) => setNewAgent({ ...newAgent, role: e.target.value })}
                        placeholder="e.g. Sprint Planner"
                        className="w-full py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none focus:border-[var(--cc-accent)]"
                      />
                    </FieldGroup>
                    <FieldGroup label="Color">
                      <div className="flex gap-2 items-center">
                        <input
                          type="color"
                          value={newAgent.color}
                          onChange={(e) => setNewAgent({ ...newAgent, color: e.target.value })}
                          className="w-8 h-8 rounded cursor-pointer border-none"
                        />
                        <input
                          value={newAgent.color}
                          onChange={(e) => setNewAgent({ ...newAgent, color: e.target.value })}
                          placeholder="#ff9f43"
                          className="flex-1 py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none focus:border-[var(--cc-accent)] font-mono"
                        />
                      </div>
                    </FieldGroup>
                    <FieldGroup label="Debate Role">
                      <select
                        value={newAgent.debate_role}
                        onChange={(e) => setNewAgent({ ...newAgent, debate_role: e.target.value })}
                        className="w-full py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none cursor-pointer focus:border-[var(--cc-accent)]"
                      >
                        <option value="analyst">Analyst</option>
                        <option value="challenger">Challenger</option>
                        <option value="proposer">Proposer</option>
                      </select>
                    </FieldGroup>
                    <FieldGroup label="Temperature">
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={0}
                          max={100}
                          value={newAgent.temperature * 100}
                          onChange={(e) => setNewAgent({ ...newAgent, temperature: Number(e.target.value) / 100 })}
                          className="flex-1 accent-[var(--cc-accent)] cursor-pointer"
                        />
                        <span className="text-[13px] font-mono text-[var(--cc-accent)] min-w-[36px]">{newAgent.temperature.toFixed(1)}</span>
                      </div>
                    </FieldGroup>
                  </div>
                  <FieldGroup label="Persona Prompt">
                    <textarea
                      value={newAgent.persona_prompt}
                      onChange={(e) => setNewAgent({ ...newAgent, persona_prompt: e.target.value })}
                      rows={4}
                      placeholder="You are the Pragmatist — you translate proposals into sprint-ready tickets..."
                      className="w-full mt-1 min-h-[80px] p-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-lg text-xs font-mono leading-relaxed text-[var(--cc-text)] resize-y outline-none focus:border-[var(--cc-accent)] transition-all duration-200"
                    />
                  </FieldGroup>
                  <FieldGroup label="Focus Areas (comma-separated)">
                    <input
                      value={newAgent.focus_areas}
                      onChange={(e) => setNewAgent({ ...newAgent, focus_areas: e.target.value })}
                      placeholder="sprint planning, effort estimation, ticket breakdown"
                      className="w-full py-2 px-3 bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-md text-[13px] text-[var(--cc-text)] outline-none focus:border-[var(--cc-accent)]"
                    />
                  </FieldGroup>
                  <div className="flex gap-3 justify-end">
                    <button
                      onClick={() => setShowAgentForm(false)}
                      className="px-4 py-2 rounded-lg border border-[var(--cc-border)] text-[var(--cc-text-muted)] text-[13px] font-medium cursor-pointer hover:border-[var(--cc-border-hover)] transition-all duration-200"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleCreateAgent}
                      className="px-4 py-2 rounded-lg bg-[var(--cc-accent)] text-white text-[13px] font-semibold cursor-pointer hover:bg-[#5a4bd4] transition-all duration-200"
                    >
                      Create Agent
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowAgentForm(true)}
                  className="w-full py-3 rounded-xl border-2 border-dashed border-[var(--cc-border)] text-[var(--cc-text-muted)] hover:border-[var(--cc-accent)] hover:text-[var(--cc-accent)] transition-all duration-200 cursor-pointer flex items-center justify-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Add Custom Agent
                </button>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Ingestion */}
        <TabsContent value="ingestion">
          <div className="card-premium p-6 space-y-5">
            <h2 className="text-base font-semibold text-[var(--cc-text)]">Ingestion Settings</h2>
            <div className="grid grid-cols-2 gap-4">
              <FieldGroup label="Max Files">
                <Input
                  type="number"
                  value={(ingest.max_files as number) || 500}
                  onChange={(e) => patch({ ingest: { ...ingest, max_files: Number(e.target.value) } })}
                  className="rounded-lg"
                />
              </FieldGroup>
              <FieldGroup label="Max File Size (KB)">
                <Input
                  type="number"
                  value={(ingest.max_file_size_kb as number) || 100}
                  onChange={(e) => patch({ ingest: { ...ingest, max_file_size_kb: Number(e.target.value) } })}
                  className="rounded-lg"
                />
              </FieldGroup>
              <FieldGroup label="Git Log Limit">
                <Input
                  type="number"
                  value={(ingest.git_log_limit as number) || 200}
                  onChange={(e) => patch({ ingest: { ...ingest, git_log_limit: Number(e.target.value) } })}
                  className="rounded-lg"
                />
              </FieldGroup>
              <FieldGroup label="Features">
                <div className="flex flex-wrap gap-2 mt-1">
                  {["AST Parse", "CVE Scan", "Secrets", "Licence", "Incremental"].map((feat) => {
                    const key = feat.toLowerCase().replace(" ", "_");
                    const active = (ingest[key] as boolean) !== false;
                    return (
                      <button
                        key={feat}
                        onClick={() => patch({ ingest: { ...ingest, [key]: !active } })}
                        className={cn(
                          "px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer transition-all duration-200",
                          active
                            ? "bg-[var(--cc-accent-muted)] border-[var(--cc-accent)] text-[var(--cc-accent)]"
                            : "bg-transparent border-[var(--cc-border)] text-[var(--cc-text-muted)] hover:border-[var(--cc-border-hover)]"
                        )}
                      >
                        {active && <Check className="w-3 h-3 inline mr-1" />}
                        {feat}
                      </button>
                    );
                  })}
                </div>
              </FieldGroup>
            </div>
            <FieldGroup label="Exclude Paths (one per line)">
              <textarea
                className="w-full rounded-xl border border-[var(--cc-border)] px-3 py-2.5 text-xs resize-y font-mono bg-[var(--cc-bg-elevated)] text-[var(--cc-text)] placeholder:text-[var(--cc-text-muted)] focus:border-[var(--cc-accent)] focus:outline-none transition-all duration-200 min-h-[100px]"
                rows={4}
                value={((ingest.exclude_paths as string[]) || ["node_modules", ".git", "dist", "build"]).join("\n")}
                onChange={(e) => patch({ ingest: { ...ingest, exclude_paths: e.target.value.split("\n").filter(Boolean) } })}
                placeholder="node_modules&#10;.git&#10;dist"
              />
            </FieldGroup>
          </div>
        </TabsContent>

        {/* Output */}
        <TabsContent value="output">
          <div className="card-premium p-6 space-y-5">
            <h2 className="text-base font-semibold text-[var(--cc-text)]">Output Settings</h2>
            <FieldGroup label="Output Formats">
              <div className="flex flex-wrap gap-2 mt-1">
                {["markdown", "json", "html", "pdf"].map((fmt) => {
                  const formats = (lc.output_formats as string[]) || ((lc.output as Record<string, unknown>)?.formats as string[]) || ["markdown"];
                  const selected = formats.includes(fmt);
                  return (
                    <button
                      key={fmt}
                      onClick={() => {
                        const updated = selected ? formats.filter((f) => f !== fmt) : [...formats, fmt];
                        patch({ output: { ...((lc.output ?? {}) as Record<string, unknown>), formats: updated } });
                      }}
                      className={cn(
                        "px-4 py-2 rounded-lg text-sm font-semibold border cursor-pointer transition-all duration-200",
                        selected
                          ? "bg-[var(--cc-accent)] border-[var(--cc-accent)] text-white shadow-[0_2px_12px_rgba(108,92,231,0.3)]"
                          : "bg-transparent border-[var(--cc-border)] text-[var(--cc-text-muted)] hover:border-[var(--cc-border-hover)] hover:text-[var(--cc-text)] hover:bg-[var(--cc-bg-hover)]"
                      )}
                    >
                      {selected && <Check className="w-3 h-3 inline mr-1.5" />}
                      {fmt.toUpperCase()}
                    </button>
                  );
                })}
              </div>
            </FieldGroup>
            <FieldGroup label="Output Directory">
              <Input
                value={((lc.output as Record<string, unknown>)?.directory as string) || "./output"}
                onChange={(e) => patch({ output: { ...((lc.output ?? {}) as Record<string, unknown>), directory: e.target.value } })}
                placeholder="./output"
                className="rounded-lg font-mono text-xs"
              />
            </FieldGroup>
            <FieldGroup label="Webhook URL">
              <Input
                value={((lc.output as Record<string, unknown>)?.webhook_url as string) || ""}
                onChange={(e) => patch({ output: { ...((lc.output ?? {}) as Record<string, unknown>), webhook_url: e.target.value } })}
                placeholder="https://hooks.example.com/codecouncil"
                className="rounded-lg text-xs"
              />
            </FieldGroup>
          </div>
        </TabsContent>
      </Tabs>

      {/* Unsaved changes toast */}
      {dirty && (
        <div className="fixed bottom-6 right-6 flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-2xl glass border border-[var(--cc-accent)] glow-sm animate-fade-in z-50">
          <div className="w-2 h-2 rounded-full bg-[var(--cc-accent)] animate-pulse-glow" />
          <span className="text-sm text-[var(--cc-text-secondary)]">Unsaved changes</span>
          <Button size="sm" onClick={handleSave} disabled={saving} className="cursor-pointer">
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      )}
    </div>
  );
}
