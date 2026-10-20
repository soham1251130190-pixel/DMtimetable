import React, { useState, useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Custom Faculty-Friendly Session Node
function SessionNode({ data, selected }) {
  const isLab = data.subjectType === 'lab';
  const isDimmed = data.isDimmed;
  const isHighlighted = data.isHighlighted;

  return (
    <div
      className={`session-node ${isLab ? 'lab-node' : 'theory-node'} ${
        isHighlighted ? 'highlighted-node' : ''
      } ${isDimmed ? 'dimmed-node' : ''}`}
    >
      <Handle type="target" position={Position.Top} className="node-handle" />
      <Handle type="source" position={Position.Bottom} className="node-handle" />
      <Handle type="target" position={Position.Left} id="left" className="node-handle" />
      <Handle type="source" position={Position.Right} id="right" className="node-handle" />

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

function FlowCanvas({ graphData }) {
  const [filterMode, setFilterMode] = useState('faculty'); // 'faculty' | 'all' | 'division'
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const reactFlowInstance = useReactFlow();

  const rawNodes = graphData?.nodes || [];
  const rawEdges = graphData?.edges || [];

  // Identify connected nodes when a node is selected
  const { connectedNodeIds, activeEdgeIds } = useMemo(() => {
    if (!selectedNodeId) {
      return { connectedNodeIds: new Set(), activeEdgeIds: new Set() };
    }
    const cNodes = new Set([selectedNodeId]);
    const aEdges = new Set();

    for (const e of rawEdges) {
      if (e.source === selectedNodeId || e.target === selectedNodeId) {
        cNodes.add(e.source);
        cNodes.add(e.target);
        aEdges.add(e.id);
      }
    }
    return { connectedNodeIds: cNodes, activeEdgeIds: aEdges };
  }, [selectedNodeId, rawEdges]);

  // Filter edges according to mode
  const filteredEdges = useMemo(() => {
    return rawEdges.filter((edge) => {
      const reasons = edge.data?.reasons || [];
      const isTeacher = reasons.includes('teacher');
      const isDivision = reasons.includes('division');

      if (filterMode === 'faculty') {
        // Show conflicts caused by shared faculty
        return isTeacher;
      }
      if (filterMode === 'division') {
        // Show conflicts caused by same student class cohort
        return isDivision && !isTeacher;
      }
      return true; // 'all'
    });
  }, [rawEdges, filterMode]);

  // Construct styled React Flow nodes with interactive dimming/highlighting
  const nodes = useMemo(() => {
    return rawNodes.map((n) => {
      const isSelected = selectedNodeId === n.id;
      const isConnected = connectedNodeIds.has(n.id);
      const isDimmed = selectedNodeId !== null && !isConnected;
      const isHighlighted = isSelected || isConnected;

      return {
        ...n,
        type: 'default',
        data: {
          ...n.data,
          isDimmed,
          isHighlighted,
          isSelected,
        },
      };
    });
  }, [rawNodes, selectedNodeId, connectedNodeIds]);

  // Construct styled React Flow edges
  const edges = useMemo(() => {
    return filteredEdges.map((e) => {
      const reasons = e.data?.reasons || [];
      const isTeacher = reasons.includes('teacher');
      const isSelectedEdge = activeEdgeIds.has(e.id);
      const isDimmed = selectedNodeId !== null && !isSelectedEdge;

      // Color coding:
      // Shared faculty: warm amber/orange
      // Same division: subtle warm slate
      let stroke = isTeacher ? '#C26118' : '#A89F91';
      let strokeWidth = isTeacher ? 2 : 1.2;
      let strokeDasharray = isTeacher ? undefined : '5 4';

      if (isSelectedEdge) {
        stroke = '#8B2E0F';
        strokeWidth = 3;
        strokeDasharray = undefined;
      }

      return {
        ...e,
        type: 'smoothstep',
        style: {
          stroke,
          strokeWidth,
          strokeDasharray,
          opacity: isDimmed ? 0.15 : 0.85,
          transition: 'all 0.2s ease',
        },
        label: isSelectedEdge ? e.label : undefined,
        labelStyle: { fill: '#3E2723', fontSize: 11, fontWeight: 700 },
        labelBgStyle: { fill: '#FFF9F0', fillOpacity: 0.95, stroke: '#C26118', strokeWidth: 1.2 },
        labelBgPadding: [6, 4],
        labelBgBorderRadius: 4,
      };
    });
  }, [filteredEdges, activeEdgeIds, selectedNodeId]);

  const onNodeClick = useCallback((event, node) => {
    setSelectedNodeId((prev) => (prev === node.id ? null : node.id));
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const selectedNodeData = useMemo(() => {
    if (!selectedNodeId) return null;
    const node = rawNodes.find((n) => n.id === selectedNodeId);
    return node?.data || null;
  }, [selectedNodeId, rawNodes]);

  const handleResetView = () => {
    setSelectedNodeId(null);
    reactFlowInstance.fitView({ padding: 0.15, duration: 400 });
  };

  return (
    <div className="graph-wrapper">
      {/* Toolbar & Filter Controls */}
      <div className="graph-toolbar">
        <div>
          <h3 className="section-title">Course Conflict & Constraint Network</h3>
          <p className="section-subtitle">
            Visual map of schedule relationships. Click any course card to highlight its direct conflicts and see why it cannot share timeslots.
          </p>
        </div>

        <div className="graph-filter-bar">
          <span className="filter-bar-label">View Filter:</span>
          <div className="filter-pill-group">
            <button
              type="button"
              className={`filter-pill-btn ${filterMode === 'faculty' ? 'active' : ''}`}
              onClick={() => setFilterMode('faculty')}
            >
              ⭐ Shared Faculty Constraints (14 links)
            </button>
            <button
              type="button"
              className={`filter-pill-btn ${filterMode === 'division' ? 'active' : ''}`}
              onClick={() => setFilterMode('division')}
            >
              👥 Class Cohort Constraints (56 links)
            </button>
            <button
              type="button"
              className={`filter-pill-btn ${filterMode === 'all' ? 'active' : ''}`}
              onClick={() => setFilterMode('all')}
            >
              All 70 Constraints
            </button>
          </div>

          <button
            type="button"
            className="btn-fit-view"
            onClick={handleResetView}
            title="Reset zoom and center view"
          >
            Center & Fit
          </button>
        </div>
      </div>

      {/* Interactive Selection Inspector Bar */}
      {selectedNodeData && (
        <div className="node-inspector-banner">
          <div className="inspector-left">
            <span className="inspector-badge">Selected Course</span>
            <strong>
              {selectedNodeData.subjectCode} — {selectedNodeData.subjectName}
            </strong>
            <span className="inspector-detail">
              Class: <strong>{selectedNodeData.divisionName}</strong> · Faculty:{' '}
              <strong>{selectedNodeData.teacherName}</strong> · Scheduled:{' '}
              <strong>{selectedNodeData.day} Period {selectedNodeData.period}</strong>
            </span>
          </div>
          <div className="inspector-right">
            <span className="conflict-count-tag">
              {connectedNodeIds.size - 1} Direct Clashes Highlighted
            </span>
            <button
              type="button"
              className="btn-clear-selection"
              onClick={() => setSelectedNodeId(null)}
            >
              Clear Focus
            </button>
          </div>
        </div>
      )}

      {/* Visual Swimlane Header above Canvas */}
      <div className="swimlane-header-row">
        <div className="swimlane-label left-lane">
          <span className="lane-dot left"></span>
          <strong>Class Cohort SE-A</strong>
          <span className="lane-sub">8 Scheduled Sessions · Rooms R103 & LAB-1</span>
        </div>
        <div className="swimlane-divider-label">
          <span>Cross-Cohort Faculty Bridge</span>
        </div>
        <div className="swimlane-label right-lane">
          <span className="lane-dot right"></span>
          <strong>Class Cohort SE-B</strong>
          <span className="lane-sub">8 Scheduled Sessions · Rooms R103 & LAB-1</span>
        </div>
      </div>

      {/* Canvas */}
      <div className="graph-canvas-box enhanced-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          fitView
          fitViewOptions={{ padding: 0.12 }}
          minZoom={0.2}
          maxZoom={1.6}
          attributionPosition="bottom-left"
        >
          <Background color="#D4CBBA" gap={24} size={1} />
          <Controls showInteractive={false} className="graph-controls" />
          <MiniMap
            nodeColor={(node) =>
              node.data?.subjectType === 'lab' ? '#D97706' : '#2D6A4F'
            }
            maskColor="rgba(248, 246, 240, 0.75)"
            className="graph-minimap"
          />
        </ReactFlow>
      </div>

      {/* Legend & Guide */}
      <div className="graph-legend-enhanced">
        <div className="legend-col">
          <span className="legend-col-title">Course Types:</span>
          <div className="legend-item">
            <span className="legend-indicator theory"></span>
            <span>Classroom Lecture (Theory)</span>
          </div>
          <div className="legend-item">
            <span className="legend-indicator lab"></span>
            <span>Laboratory Practical (Lab)</span>
          </div>
        </div>

        <div className="legend-col">
          <span className="legend-col-title">Constraint Lines:</span>
          <div className="legend-item">
            <span className="legend-line faculty"></span>
            <span>
              <strong>Shared Faculty (Amber):</strong> Same professor cannot teach two classes simultaneously
            </span>
          </div>
          <div className="legend-item">
            <span className="legend-line cohort"></span>
            <span>
              <strong>Same Cohort (Dashed Grey):</strong> Students cannot attend two lectures at the same time
            </span>
          </div>
        </div>

        <div className="legend-tip">
          💡 <em>Tip: Click any course card to isolate its conflicts and inspect why it was scheduled at its time period.</em>
        </div>
      </div>
    </div>
  );
}

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

  return (
    <ReactFlowProvider>
      <FlowCanvas graphData={graphData} />
    </ReactFlowProvider>
  );
}
