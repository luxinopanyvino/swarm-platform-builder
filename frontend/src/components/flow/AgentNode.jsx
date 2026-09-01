import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Search, PenLine, Eye, FileText, Send, Bot, Zap } from 'lucide-react';

const AGENT_META = {
  investigador: { icon: Search,   color: 'var(--agent-research)', label: 'Investigador', desc: 'Busca contexto en RAG y APIs científicas' },
  redactor:     { icon: PenLine,  color: 'var(--agent-write)', label: 'Redactor',     desc: 'Genera borrador con Ollama' },
  revisor:      { icon: Eye,      color: 'var(--agent-review)', label: 'Revisor',      desc: 'Evalúa calidad (score 0-100)' },
  formateador:  { icon: FileText, color: 'var(--agent-format)', label: 'Formateador',  desc: 'Aplica formato APA/IEEE/Vancouver' },
  publicador:   { icon: Send,     color: 'var(--agent-publish)', label: 'Publicador',   desc: 'Publica el artículo en DB' },
};

// Agents that truly query RAG by themselves (not via pipeline state)
const AGENTS_WITH_OWN_RAG = new Set(['investigador']);

export const AgentNode = memo(({ data, selected }) => {
  const fallbackMeta = AGENT_META[data.agentId] || {};
  const meta = {
    Icon:  fallbackMeta.icon  || Bot,
    color: data.color || fallbackMeta.color || 'var(--neutral-60)',
    label: data.label || fallbackMeta.label || data.agentId,
    desc:  data.desc  || fallbackMeta.desc  || '',
  };

  return (
    <div className={`agent-node${selected ? ' selected' : ''}`}
      style={{ borderColor: selected ? meta.color : undefined }}>
      <Handle type="target" position={Position.Left}
        style={{ background: meta.color, border: `2px solid ${meta.color}` }} />

      <div className="agent-node-header">
        <span className="agent-node-icon"
          style={{ width: 22, height: 22, display: 'flex', alignItems: 'center', justifyContent: 'center',
                   background: `${meta.color}18`, borderRadius: 4 }}>
          <meta.Icon size={13} style={{ color: meta.color }} strokeWidth={1.5} />
        </span>
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
            <div className="agent-node-badge" style={{ marginTop: 0, background: 'var(--blue-05)', color: 'var(--blue-60)' }}>
              {data.model}
            </div>
          )}
          {data.ragEnabled && AGENTS_WITH_OWN_RAG.has(data.agentId) && (
            <div className="agent-node-badge" style={{ marginTop: 0, background: 'var(--green-05)', color: 'var(--green-60)' }}>
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
    <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 4 }}>
      <Zap size={16} style={{ color: 'var(--warning)' }} strokeWidth={1.5} />
    </div>
    <div className="condition-node-label">{data.label || 'Condición'}</div>
    {data.expression && (
      <div className="condition-node-expr">{data.expression}</div>
    )}
    <Handle type="source" position={Position.Right} id="true"
      style={{ top: '30%', background: 'var(--agent-format)', border: '2px solid var(--agent-format)' }} />
    <Handle type="source" position={Position.Right} id="false"
      style={{ top: '70%', background: 'var(--red-60)', border: '2px solid var(--red-60)' }} />
  </div>
));

export const nodeTypes = {
  agent: AgentNode,
  condition: ConditionNode,
};

export { AGENT_META };
