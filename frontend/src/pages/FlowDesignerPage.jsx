import React, { useCallback, useEffect, useRef } from 'react';
import {
  ReactFlow, Background, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState, Panel,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useNavigate, useLocation } from 'react-router-dom';
import { Pencil, Plus, Save, Play, Trash2, GitBranch } from 'lucide-react';
import { nodeTypes, AGENT_META } from '../components/flow/AgentNode';
import { AgentCreateModal, AgentEditorModal } from '../components/agents/AgentEditorModal';
import { useFlowStore } from '../store/flowStore';
import { useArticleStore } from '../store/articleStore';
import { useProjectStore } from '../store/projectStore';
import { agentsApi } from '../api/agents';
import toast from 'react-hot-toast';

const BUILTIN_IDS = new Set(['investigador', 'redactor', 'revisor', 'formateador', 'publicador', 'orquestador']);

let nodeId = 100;
const newId = () => `node_${++nodeId}`;

export default function FlowDesignerPage() {
  const navigate = useNavigate();
  const location = useLocation();
  // When navigating from ArticleDetailPage, an existing article can be passed
  const existingArticleId = location.state?.existingArticleId || null;
  const existingArticleTitle = location.state?.existingArticleTitle || '';
  const {
    draftNodes, draftEdges, draftName,
    setDraftNodes, setDraftEdges, setDraftName,
    saveFlow, saveDraftLocally, loadLocalDraft, clearLocalDraft,
    activeFlow,
  } = useFlowStore();
  const { createArticle, updateArticle } = useArticleStore();
  const { activeProject } = useProjectStore();

  const [nodes, setNodes, onNodesChange] = useNodesState(draftNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(draftEdges);
  const [flowName, setFlowName] = React.useState(draftName);
  const [saving, setSaving] = React.useState(false);
  const [showRunModal, setShowRunModal] = React.useState(false);
  const [runTitle, setRunTitle] = React.useState(existingArticleTitle);
  const [runKeywords, setRunKeywords] = React.useState([]);
  const [runKeywordInput, setRunKeywordInput] = React.useState('');
  const [runDescription, setRunDescription] = React.useState('');
  const [runOutline, setRunOutline] = React.useState('');
  const [models, setModels] = React.useState(['llama3.2:1b']);
  const [paletteAgents, setPaletteAgents] = React.useState([]);
  const [editAgent, setEditAgent] = React.useState(null);
  const [showNewAgent, setShowNewAgent] = React.useState(false);
  const reactFlowWrapper = useRef(null);
  const [rfInstance, setRfInstance] = React.useState(null);

  const buildPaletteAgent = useCallback((agent) => {
    const meta = AGENT_META[agent.slug] || AGENT_META[agent.id] || {};
    return {
      id: agent.slug || agent.id,
      content: agent.content,
      model: agent.model,
      temperature: agent.temperature,
      prompt_template: agent.prompt_template,
      rag_enabled: agent.rag_enabled,
      rag_collection: agent.rag_collection,
      scientific_format: agent.scientific_format,
      output_language: agent.output_language,
      target_word_count: agent.target_word_count,
      emoji: meta.emoji || '🤖',
      color: meta.color || '#6b6b8a',
      label: meta.label || agent.name || agent.slug || agent.id,
      desc: meta.desc || `Perfil ${agent.slug || agent.id}`,
    };
  }, []);

  const loadPaletteAgents = useCallback(async () => {
    try {
      const projectId = activeProject?.id;
      if (!projectId) {
        setPaletteAgents(Object.entries(AGENT_META).map(([id, meta]) => ({ id, ...meta })));
        return;
      }
      const defs = await agentsApi.getClaudeDefs(projectId);
      setPaletteAgents(defs.map(buildPaletteAgent));
    } catch {
      setPaletteAgents(Object.entries(AGENT_META).map(([id, meta]) => ({ id, ...meta })));
    }
  }, [buildPaletteAgent, activeProject?.id]);

  // Auto-checkpoint every 30s
  useEffect(() => {
    const timer = setInterval(() => {
      setDraftNodes(nodes);
      setDraftEdges(edges);
      setDraftName(flowName);
      saveDraftLocally();
    }, 30000);
    return () => clearInterval(timer);
  }, [nodes, edges, flowName]);

  // Check for local draft on mount
  useEffect(() => {
    if (!activeFlow) {
      const draft = loadLocalDraft();
      if (draft && draft.draftNodes?.length > 0) {
        toast((t) => (
          <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            Tienes un borrador sin guardar
            <button className="btn btn-primary btn-sm" onClick={() => {
              setNodes(draft.draftNodes);
              setEdges(draft.draftEdges);
              setFlowName(draft.draftName);
              toast.dismiss(t.id);
            }}>Restaurar</button>
            <button className="btn btn-ghost btn-sm" onClick={() => {
              clearLocalDraft(); toast.dismiss(t.id);
            }}>Descartar</button>
          </span>
        ), { duration: 10000 });
      }
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    loadPaletteAgents();
    agentsApi.getModels().then((response) => {
      if (mounted) {
        setModels(response.models || ['llama3.2:1b']);
      }
    }).catch(() => {});
    return () => {
      mounted = false;
    };
  }, [loadPaletteAgents]);

  useEffect(() => {
    if (paletteAgents.length === 0) {
      return;
    }

    setNodes((current) => current.map((node) => {
      if (node.type !== 'agent') {
        return node;
      }

      const paletteAgent = paletteAgents.find((agent) => agent.id === node.data?.agentId);
      if (!paletteAgent) {
        return node;
      }

      return {
        ...node,
        data: {
          ...node.data,
          label: paletteAgent.label,
          emoji: paletteAgent.emoji,
          color: paletteAgent.color,
          desc: paletteAgent.desc,
          model: paletteAgent.model,
          ragEnabled: paletteAgent.rag_enabled,
          scientificFormat: paletteAgent.scientific_format,
          outputLanguage: paletteAgent.output_language,
          targetWordCount: paletteAgent.target_word_count,
        },
      };
    }));
  }, [paletteAgents, setNodes]);

  const onConnect = useCallback((params) => {
    setEdges(eds => addEdge({ ...params, animated: true, style: { stroke: 'var(--brand-primary)' } }, eds));
  }, []);

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    const agentId = e.dataTransfer.getData('application/agentId');
    if (!agentId) return;

    const bounds = reactFlowWrapper.current.getBoundingClientRect();
    const position = rfInstance.screenToFlowPosition({
      x: e.clientX - bounds.left,
      y: e.clientY - bounds.top,
    });

    const agent = paletteAgents.find((entry) => entry.id === agentId);

    const node = {
      id: newId(),
      type: 'agent',
      position,
      data: {
        agentId,
        label: agent?.label || AGENT_META[agentId]?.label || agentId,
        emoji: agent?.emoji,
        color: agent?.color,
        desc: agent?.desc,
        model: agent?.model,
        ragEnabled: agent?.rag_enabled,
        scientificFormat: agent?.scientific_format,
        outputLanguage: agent?.output_language,
        targetWordCount: agent?.target_word_count,
      },
    };

    setNodes(nds => [...nds, node]);
  }, [paletteAgents, rfInstance]);

  const handleSave = async () => {
    setSaving(true);
    setDraftNodes(nodes);
    setDraftEdges(edges);
    setDraftName(flowName);
    try {
      await saveFlow();
      clearLocalDraft();
      toast.success('Flujo guardado');
    } catch {
      toast.error('Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    const titleValue = runTitle.trim();
    if (!titleValue && !existingArticleId) { toast.error('Escribe un título para el artículo'); return; }
    try {
      let articleId;
      if (existingArticleId) {
        // Re-run on existing article; optionally update the title if user changed it
        articleId = existingArticleId;
        if (titleValue && titleValue !== existingArticleTitle) {
          await updateArticle(existingArticleId, { title: titleValue });
        }
      } else {
        const article = await createArticle(titleValue);
        articleId = article.id;
      }
      setShowRunModal(false);
      const agentNodes = nodes.filter(n => n.type === 'agent');
      const flowSequence = agentNodes.map(n => n.data.agentId);
      // Build per-agent model settings from node data
      const agentSettings = {};
      agentNodes.forEach(n => {
        if (n.data.agentId && n.data.model) {
          agentSettings[n.data.agentId] = {
            model: n.data.model,
            ...(n.data.scientificFormat ? { scientific_format: n.data.scientificFormat } : {}),
            ...(n.data.outputLanguage ? { output_language: n.data.outputLanguage } : {}),
            ...(n.data.targetWordCount ? { target_word_count: n.data.targetWordCount } : {}),
          };
        }
      });
      navigate(`/execution/${articleId}`, {
        state: {
          flowNodes: nodes,
          flowEdges: edges,
          flowSequence,
          agentSettings,
          keywords: runKeywords,
          contextDescription: runDescription,
          articleOutline: runOutline,
        }
      });
    } catch { toast.error('Error al iniciar pipeline'); }
  };

  return (
    <div className="flow-designer-layout">
      {/* Agent Palette */}
      <div className="flow-palette">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
          <div className="palette-title" style={{ marginBottom: 0 }}>Agentes</div>
          <button className="btn btn-primary btn-sm" onClick={() => setShowNewAgent(true)}>
            <Plus size={13} /> Nuevo
          </button>
        </div>
        {paletteAgents.map(agent => (
          <div
            key={agent.id}
            className="palette-node"
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData('application/agentId', agent.id);
              e.dataTransfer.effectAllowed = 'move';
            }}
          >
            <div className="palette-node-icon" style={{ background: `${agent.color}20` }}>
              {agent.emoji}
            </div>
            <div>
              <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>{agent.label}</div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>{agent.desc}</div>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{ marginTop: 'var(--space-2)', paddingInline: 0 }}
                draggable={false}
                onMouseDown={(event) => event.stopPropagation()}
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  setEditAgent(agent);
                }}
              >
                <Pencil size={12} /> Editar
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Canvas */}
      <div className="flow-canvas-area" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setRfInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode="Delete"
        >
          <Background variant="dots" gap={20} size={1} />
          <Controls />
          <MiniMap
            nodeColor={(n) => {
              if (n.type === 'condition') return '#c47d04';
              return n.data?.color || AGENT_META[n.data?.agentId]?.color || '#8793a5';
            }}
            maskColor="rgba(244,246,249,0.6)"
          />

          {/* Toolbar */}
          <Panel position="top-center">
            <div className="flow-toolbar">
              <input
                className="input"
                style={{ width: 200, padding: '6px 10px' }}
                value={flowName}
                onChange={e => setFlowName(e.target.value)}
                placeholder="Nombre del flujo"
              />
              <div className="divider" style={{ width: 1, height: 24, margin: '0 4px' }} />
              <button className="btn btn-ghost btn-sm btn-icon" title="Limpiar canvas"
                onClick={() => { setNodes([]); setEdges([]); }}>
                <Trash2 size={15} />
              </button>
              <button className="btn btn-secondary btn-sm" onClick={handleSave} disabled={saving}>
                <Save size={14} />
                {saving ? 'Guardando…' : 'Guardar'}
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => setShowRunModal(true)}
                disabled={nodes.filter(n => n.type === 'agent').length === 0}>
                <Play size={14} />
                Ejecutar
              </button>
            </div>
          </Panel>
        </ReactFlow>

        {/* Empty state */}
        {nodes.length === 0 && (
          <div className="empty-state" style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0 }}>
            <div className="empty-state-icon">
              <GitBranch size={28} />
            </div>
            <h3>Diseña tu pipeline</h3>
            <p>Arrastra agentes desde el panel izquierdo al canvas para crear tu flujo de trabajo.</p>
          </div>
        )}
      </div>

      {/* Run Modal */}
      {showRunModal && (
        <div className="modal-backdrop" onClick={() => setShowRunModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Ejecutar pipeline</h3>
              <button className="btn btn-ghost btn-sm btn-icon" onClick={() => setShowRunModal(false)}>✕</button>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {existingArticleId ? (
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: 0 }}>
                  Re-ejecutando pipeline <strong style={{ color: 'var(--text-primary)' }}>{flowName}</strong> sobre el artículo existente. Puedes cambiar el título a continuación.
                </p>
              ) : (
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: 0 }}>
                  Se creará un nuevo artículo y se ejecutará el pipeline <strong style={{ color: 'var(--text-primary)' }}>{flowName}</strong> sobre él.
                </p>
              )}

              <div className="input-group">
                <label htmlFor="run-title" className="input-label">
                  Título del artículo
                  {existingArticleId && <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: 6 }}>— opcional, deja igual para mantener el actual</span>}
                </label>
                <input
                  id="run-title"
                  className="input"
                  placeholder={existingArticleId ? existingArticleTitle : 'Ej: El impacto del cambio climático en ecosistemas marinos'}
                  value={runTitle}
                  onChange={e => setRunTitle(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && document.getElementById('kw-input')?.focus()}
                  autoFocus
                />
              </div>

              <div className="input-group">
                <label htmlFor="kw-input" className="input-label">
                  Palabras clave
                  <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: 6 }}>— orientan la búsqueda del Investigador</span>
                </label>
                <div style={{
                  display: 'flex', flexWrap: 'wrap', gap: 6, padding: '6px 10px',
                  background: 'var(--bg-input)', border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)', minHeight: 42, alignItems: 'center',
                }}>
                  {runKeywords.map(kw => (
                    <span key={kw} style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      background: 'rgba(99,102,241,0.18)', color: '#a5b4fc',
                      borderRadius: 20, padding: '2px 10px', fontSize: 'var(--font-size-xs)', fontWeight: 500,
                    }}>
                      {kw}
                      <button
                        type="button"
                        onClick={() => setRunKeywords(ks => ks.filter(k => k !== kw))}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#a5b4fc', lineHeight: 1, padding: 0 }}
                        aria-label={`Eliminar keyword ${kw}`}
                      >×</button>
                    </span>
                  ))}
                  <input
                    id="kw-input"
                    style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)', minWidth: 120, flex: 1 }}
                    placeholder={runKeywords.length === 0 ? 'Escribe y pulsa Enter o coma…' : ''}
                    value={runKeywordInput}
                    onChange={e => setRunKeywordInput(e.target.value)}
                    onKeyDown={e => {
                      if ((e.key === 'Enter' || e.key === ',') && runKeywordInput.trim()) {
                        e.preventDefault();
                        const kw = runKeywordInput.trim().replace(/,$/, '');
                        if (kw && !runKeywords.includes(kw)) setRunKeywords(ks => [...ks, kw]);
                        setRunKeywordInput('');
                      } else if (e.key === 'Backspace' && !runKeywordInput && runKeywords.length > 0) {
                        setRunKeywords(ks => ks.slice(0, -1));
                      }
                    }}
                    aria-label="Añadir palabra clave"
                  />
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: 4 }}>
                  Si no se proporcionan, se extraen automáticamente del título.
                </div>
              </div>

              <div className="input-group">
                <label htmlFor="run-description" className="input-label">
                  Descripción / enfoque
                  <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: 6 }}>— opcional</span>
                </label>
                <textarea
                  id="run-description"
                  className="input"
                  rows={3}
                  placeholder="Ej: Enfocado en arrecifes de coral del Caribe, con énfasis en acidificación oceánica y pérdida de biodiversidad post-2010."
                  value={runDescription}
                  onChange={e => setRunDescription(e.target.value)}
                  style={{ resize: 'vertical', fontSize: 'var(--font-size-sm)' }}
                />
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: 4 }}>
                  El <strong>Investigador</strong> la usa para afinar la búsqueda semántica. El <strong>Redactor</strong> la recibe como instrucción de enfoque en el prompt.
                </div>
              </div>

              <div className="input-group">
                <label htmlFor="run-outline" className="input-label">
                  Estructura / Esquema del artículo
                  <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: 6 }}>— opcional</span>
                </label>
                <textarea
                  id="run-outline"
                  className="input"
                  rows={3}
                  placeholder="Ej:&#10;- Introducción: Contexto del cambio climático&#10;- Sección 1: Acidificación oceánica&#10;- Sección 2: Consecuencias ecológicas&#10;- Conclusiones generales"
                  value={runOutline}
                  onChange={e => setRunOutline(e.target.value)}
                  style={{ resize: 'vertical', fontSize: 'var(--font-size-sm)' }}
                />
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: 4 }}>
                  Define las secciones, subsecciones o títulos creativos que el <strong>Redactor</strong> debe seguir obligatoriamente.
                </div>
              </div>

              <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: 'var(--space-3)', fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                <strong style={{ color: 'var(--text-secondary)' }}>Secuencia:</strong>{' '}
                {nodes.filter(n => n.type === 'agent').map((n) => {
                  const meta = AGENT_META[n.data?.agentId] || {};
                  return `${n.data?.emoji || meta.emoji || '🤖'} ${n.data?.label || meta.label || n.data?.agentId}`;
                }).join(' → ')}
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setShowRunModal(false)}>Cancelar</button>
              <button className="btn btn-primary" onClick={handleRun}>
                <Play size={14} /> Ejecutar pipeline
              </button>
            </div>
          </div>
        </div>
      )}

      {editAgent && (
        <AgentEditorModal
          agent={editAgent}
          isBuiltin={BUILTIN_IDS.has(editAgent.id)}
          models={models}
          onClose={() => setEditAgent(null)}
          onSaved={async () => {
            setEditAgent(null);
            await loadPaletteAgents();
          }}
          onDeleted={(id) => {
            setEditAgent(null);
            setPaletteAgents((current) => current.filter((agent) => agent.id !== id));
            setNodes((current) => current.filter((node) => node.data?.agentId !== id));
          }}
        />
      )}

      {showNewAgent && (
        <AgentCreateModal
          builtInIds={BUILTIN_IDS}
          onClose={() => setShowNewAgent(false)}
          onCreate={async (payload) => {
            await agentsApi.createClaudeDef(payload);
            toast.success(`Agente "${payload.name}" creado`);
            await loadPaletteAgents();
          }}
        />
      )}
    </div>
  );
}
