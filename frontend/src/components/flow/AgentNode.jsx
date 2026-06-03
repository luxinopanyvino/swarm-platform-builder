import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';

const AGENT_META = {
  investigador: { emoji: '🔍', color: '#06b6d4', label: 'Investigador', desc: 'Busca contexto en RAG y APIs científicas' },
  redactor:     { emoji: '✍️',  color: '#7c3aed', label: 'Redactor',     desc: 'Genera borrador con Ollama' },
  revisor:      { emoji: '👁️',  color: '#f59e0b', label: 'Revisor',      desc: 'Evalúa calidad (score 0-100)' },
  formateador:  { emoji: '📄',  color: '#10b981', label: 'Formateador',  desc: 'Aplica formato APA/IEEE/Vancouver' },
  publicador:   { emoji: '🚀',  color: '#ef4444', label: 'Publicador',   desc: 'Publica el artículo en DB' },
};

// Agents that truly query RAG by themselves (not via pipeline state)
const AGENTS_WITH_OWN_RAG = new Set(['investigador']);

export const AgentNode = memo(({ data, selected }) => {
  const fallbackMeta = AGENT_META[data.agentId] || {};
  const meta = {
    emoji: data.emoji || fallbackMeta.emoji || '🤖',
    color: data.color || fallbackMeta.color || '#6b6b8a',
    label: data.label || fallbackMeta.label || data.agentId,
    desc: data.desc || fallbackMeta.desc || '',
  };

  return (
    <div className={`agent-node${selected ? ' selected' : ''}`}
      style={{ borderColor: selected ? meta.color : undefined }}>
      <Handle type="target" position={Position.Left}
        style={{ background: meta.color, border: `2px solid ${meta.color}` }} />

      <div className="agent-node-header">
        <span className="agent-node-icon">{meta.emoji}</span>
        <span className="agent-node-name">{meta.label}</span>
      </div>
      <div className="agent-node-desc">{meta.desc}</div>
      <div className="agent-node-badge"
        style={{ background: `${meta.color}20`, color: meta.color }}>
        agent
      </div>
      {(data.model || (data.ragEnabled && AGENTS_WITH_OWN_RAG.has(data.agentId))) && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
          {data.model && (
            <div className="agent-node-badge" style={{ marginTop: 0, background: 'rgba(59,130,246,0.14)', color: '#60a5fa' }}>
              {data.model}
            </div>
          )}
          {data.ragEnabled && AGENTS_WITH_OWN_RAG.has(data.agentId) && (
            <div className="agent-node-badge" style={{ marginTop: 0, background: 'rgba(16,185,129,0.14)', color: '#34d399' }}>
              RAG
            </div>
          )}
        </div>
      )}

      <Handle type="source" position={Position.Right}
        style={{ background: meta.color, border: `2px solid ${meta.color}` }} />
    </div>
  );
});

export const ConditionNode = memo(({ data, selected }) => (
  <div className={`condition-node${selected ? ' selected' : ''}`}>
    <Handle type="target" position={Position.Left} />
    <div style={{ fontSize: 18, marginBottom: 4 }}>⚡</div>
    <div className="condition-node-label">{data.label || 'Condición'}</div>
    {data.expression && (
      <div className="condition-node-expr">{data.expression}</div>
    )}
    <Handle type="source" position={Position.Right} id="true"
      style={{ top: '30%', background: '#10b981', border: '2px solid #10b981' }} />
    <Handle type="source" position={Position.Right} id="false"
      style={{ top: '70%', background: '#ef4444', border: '2px solid #ef4444' }} />
  </div>
));

export const nodeTypes = {
  agent: AgentNode,
  condition: ConditionNode,
};

export { AGENT_META };
