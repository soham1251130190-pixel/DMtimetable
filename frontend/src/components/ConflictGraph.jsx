import React, { useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Custom Faculty-Friendly Session Node
function SessionNode({ data }) {
  const isLab = data.subjectType === 'lab';

  return (
    <div className={`session-node ${isLab ? 'lab-node' : 'theory-node'}`}>
      <Handle type="target" position={Position.Top} className="node-handle" />
      <Handle type="source" position={Position.Bottom} className="node-handle" />
      
      <div className="node-header">
        <span className="node-subject-code">{data.subjectCode || 'Session'}</span>
        <span className={`node-type-badge ${isLab ? 'badge-lab' : 'badge-theory'}`}>
          {isLab ? 'Lab' : 'Theory'}
        </span>
      </div>

      <div className="node-title" title={data.subjectName}>
        {data.subjectName || data.label || 'Course Lecture'}
      </div>

      <div className="node-details">
        <div className="node-row">
          <span className="node-label">Class:</span>
          <span className="node-val highlight-class">{data.divisionName || 'Class'}</span>
        </div>
        <div className="node-row">
          <span className="node-label">Faculty:</span>
          <span className="node-val">{data.teacherName || 'Faculty'}</span>
        </div>
        {data.roomName && (
          <div className="node-row">
            <span className="node-label">Room:</span>
            <span className="node-val">{data.roomName}</span>
          </div>
        )}
      </div>

      {data.day && data.period && (
        <div className="node-footer">
          <span>{data.day} · Period {data.period}</span>
          {data.startTime && <span className="node-time">{data.startTime}</span>}
        </div>
      )}
    </div>
  );
}

const nodeTypes = {
  default: SessionNode,
  sessionNode: SessionNode,
};

export default function ConflictGraph({ graphData, loading, error }) {
  if (loading) {
    return (
      <div className="graph-container-empty">
        <div className="loading-spinner"></div>
        <p>Loading course conflict network...</p>
      </div>
    );
  }

  if (error || !graphData) {
    return (
      <div className="graph-container-empty error">
        <p className="error-title">Unable to display conflict network</p>
        <p className="error-desc">{error || 'Network data could not be retrieved.'}</p>
      </div>
    );
  }

  const nodes = useMemo(() => {
    if (!graphData.nodes) return [];
    return graphData.nodes.map(n => ({
      ...n,
      type: 'default',
    }));
  }, [graphData.nodes]);

  const edges = useMemo(() => {
    if (!graphData.edges) return [];
    return graphData.edges.map(e => ({
      ...e,
      animated: false,
      style: { stroke: '#A69B8D', strokeWidth: 1.5 },
      labelStyle: { fill: '#4A443C', fontSize: 11, fontWeight: 500 },
      labelBgStyle: { fill: '#FBF9F5', fillOpacity: 0.95, stroke: '#D9D0C1', strokeWidth: 1 },
      labelBgPadding: [6, 4],
      labelBgBorderRadius: 4,
    }));
  }, [graphData.edges]);

  const meta = graphData.metadata || {};

  return (
    <div className="graph-wrapper">
      <div className="graph-toolbar">
        <div>
          <h3 className="section-title">Course Conflict & Constraint Network</h3>
          <p className="section-subtitle">
            Visualizing scheduling connections between lecture sessions. Linked sessions share faculty, student cohorts, or course choices.
          </p>
        </div>
        <div className="graph-stats-pills">
          <span className="pill">
            <strong>{nodes.length}</strong> Sessions
          </span>
          <span className="pill">
            <strong>{edges.length}</strong> Conflict Links
          </span>
          {meta.color_lower_bound && (
            <span className="pill accent">
              Min Periods Needed: <strong>{meta.color_lower_bound}</strong>
            </span>
          )}
        </div>
      </div>

      <div className="graph-canvas-box">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={1.5}
          attributionPosition="bottom-left"
        >
          <Background color="#D6CEBF" gap={20} size={1} />
          <Controls showInteractive={false} className="graph-controls" />
          <MiniMap
            nodeColor="#C7BDAE"
            maskColor="rgba(248, 246, 240, 0.75)"
            className="graph-minimap"
          />
        </ReactFlow>
      </div>

      <div className="graph-legend">
        <div className="legend-item">
          <span className="legend-indicator theory"></span>
          <span>Classroom Lecture (Theory)</span>
        </div>
        <div className="legend-item">
          <span className="legend-indicator lab"></span>
          <span>Laboratory Practical (Lab)</span>
        </div>
        <div className="legend-item">
          <span className="legend-line"></span>
          <span>Scheduling Constraint (Shared Faculty / Class Cohort)</span>
        </div>
      </div>
    </div>
  );
}
