import { useMemo } from "react";
import { ReactFlow, Background, Controls, MarkerType, type Node, type Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { HierarchyResponse, HierarchyItem, HierarchyEpic } from "@/lib/hierarchy";

interface HierarchyViewProps {
  hierarchy: HierarchyResponse | null;
  viewMode: "list" | "flow";
  onItemClick?: (item: HierarchyItem) => void;
}

function getItemTypeColor(type: string | null): string {
  switch (type) {
    case "story":
      return "#3b82f6"; // blue
    case "task":
      return "#10b981"; // green
    case "feature":
      return "#8b5cf6"; // purple
    case "bug":
      return "#ef4444"; // red
    default:
      return "#6b7280"; // gray
  }
}

function getItemTypeBgColor(type: string | null): string {
  switch (type) {
    case "story":
      return "#dbeafe";
    case "task":
      return "#d1fae5";
    case "feature":
      return "#ede9fe";
    case "bug":
      return "#fee2e2";
    default:
      return "#f3f4f6";
  }
}

export function HierarchyView({ hierarchy, viewMode, onItemClick }: HierarchyViewProps) {
  const { nodes, edges } = useMemo(() => {
    if (!hierarchy || viewMode !== "flow") {
      return { nodes: [], edges: [] };
    }

    const nodes: Node[] = [];
    const edges: Edge[] = [];
    let yOffset = 0;
    const EPIC_SPACING = 300;
    const ITEM_SPACING = 100;
    const HORIZONTAL_SPACING = 250;

    // Process each epic
    hierarchy.epics.forEach((epic, epicIndex) => {
      const epicNodeId = `epic-${epic.epic_option_id || "no-epic"}`;

      // Create epic node
      nodes.push({
        id: epicNodeId,
        type: "default",
        position: { x: 0, y: yOffset },
        data: {
          label: epic.epic_name || "Sem Épico",
        },
        style: {
          background: "#f97316",
          color: "white",
          border: "2px solid #ea580c",
          borderRadius: "8px",
          padding: "12px 20px",
          fontSize: "14px",
          fontWeight: "600",
          minWidth: "200px",
        },
      });

      let itemYOffset = yOffset + ITEM_SPACING;

      // Process epic items recursively
      const processItem = (item: HierarchyItem, level: number, parentId: string) => {
        const itemNodeId = `item-${item.id}`;
        const xPos = level * HORIZONTAL_SPACING;

        nodes.push({
          id: itemNodeId,
          type: "default",
          position: { x: xPos, y: itemYOffset },
          data: {
            label: (
              <div className="flex flex-col gap-1">
                <div className="font-medium text-sm truncate" style={{ maxWidth: "180px" }}>
                  {item.title || "Sem título"}
                </div>
                <div className="flex gap-1">
                  {item.item_type && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded" style={{
                      background: getItemTypeBgColor(item.item_type),
                      color: getItemTypeColor(item.item_type),
                      fontWeight: "600"
                    }}>
                      {item.item_type}
                    </span>
                  )}
                  {item.status && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-700">
                      {item.status}
                    </span>
                  )}
                </div>
              </div>
            ),
          },
          style: {
            background: "white",
            border: `2px solid ${getItemTypeColor(item.item_type)}`,
            borderRadius: "6px",
            padding: "8px 12px",
            minWidth: "200px",
            cursor: onItemClick ? "pointer" : "default",
          },
        });

        // Create edge from parent
        edges.push({
          id: `${parentId}-${itemNodeId}`,
          source: parentId,
          target: itemNodeId,
          type: "smoothstep",
          animated: false,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: getItemTypeColor(item.item_type),
          },
          style: {
            stroke: getItemTypeColor(item.item_type),
            strokeWidth: 2,
          },
        });

        itemYOffset += ITEM_SPACING;

        // Process children
        if (item.children && item.children.length > 0) {
          item.children.forEach((child) => {
            processItem(child, level + 1, itemNodeId);
          });
        }
      };

      // Process all root items in this epic
      epic.items.forEach((item) => {
        processItem(item, 1, epicNodeId);
      });

      yOffset = itemYOffset + EPIC_SPACING;
    });

    // Process orphans if any
    if (hierarchy.orphans.length > 0) {
      const orphanNodeId = "epic-orphans";

      nodes.push({
        id: orphanNodeId,
        type: "default",
        position: { x: 0, y: yOffset },
        data: { label: "Outros (sem épico)" },
        style: {
          background: "#6b7280",
          color: "white",
          border: "2px solid #4b5563",
          borderRadius: "8px",
          padding: "12px 20px",
          fontSize: "14px",
          fontWeight: "600",
          minWidth: "200px",
        },
      });

      let orphanYOffset = yOffset + ITEM_SPACING;

      hierarchy.orphans.forEach((item) => {
        const processOrphan = (orphan: HierarchyItem, level: number, parentId: string) => {
          const itemNodeId = `item-${orphan.id}`;
          const xPos = level * HORIZONTAL_SPACING;

          nodes.push({
            id: itemNodeId,
            type: "default",
            position: { x: xPos, y: orphanYOffset },
            data: {
              label: (
                <div className="flex flex-col gap-1">
                  <div className="font-medium text-sm truncate" style={{ maxWidth: "180px" }}>
                    {orphan.title || "Sem título"}
                  </div>
                  <div className="flex gap-1">
                    {orphan.item_type && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{
                        background: getItemTypeBgColor(orphan.item_type),
                        color: getItemTypeColor(orphan.item_type),
                        fontWeight: "600"
                      }}>
                        {orphan.item_type}
                      </span>
                    )}
                  </div>
                </div>
              ),
            },
            style: {
              background: "white",
              border: `2px solid ${getItemTypeColor(orphan.item_type)}`,
              borderRadius: "6px",
              padding: "8px 12px",
              minWidth: "200px",
              cursor: onItemClick ? "pointer" : "default",
            },
          });

          edges.push({
            id: `${parentId}-${itemNodeId}`,
            source: parentId,
            target: itemNodeId,
            type: "smoothstep",
            animated: false,
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: getItemTypeColor(orphan.item_type),
            },
            style: {
              stroke: getItemTypeColor(orphan.item_type),
              strokeWidth: 2,
            },
          });

          orphanYOffset += ITEM_SPACING;

          if (orphan.children && orphan.children.length > 0) {
            orphan.children.forEach((child) => {
              processOrphan(child, level + 1, itemNodeId);
            });
          }
        };

        processOrphan(item, 1, orphanNodeId);
      });
    }

    return { nodes, edges };
  }, [hierarchy, viewMode, onItemClick]);

  if (!hierarchy) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        Nenhuma hierarquia encontrada
      </div>
    );
  }

  if (viewMode === "flow") {
    return (
      <div className="h-[800px] w-full border rounded-lg">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          attributionPosition="bottom-left"
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    );
  }

  // List view
  return (
    <div className="space-y-4">
      {hierarchy.epics.map((epic) => (
        <EpicListCard key={epic.epic_option_id || "no-epic"} epic={epic} onItemClick={onItemClick} />
      ))}

      {hierarchy.orphans.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <h3 className="font-semibold text-lg mb-4 text-muted-foreground">
              Outros (sem épico)
            </h3>
            <div className="space-y-2">
              {hierarchy.orphans.map((item) => (
                <ItemRow key={item.id} item={item} level={0} onItemClick={onItemClick} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function EpicListCard({ epic, onItemClick }: { epic: HierarchyEpic; onItemClick?: (item: HierarchyItem) => void }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
          <span className="text-2xl">📦</span>
          {epic.epic_name || "Sem Épico"}
        </h3>
        {epic.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum item neste épico</p>
        ) : (
          <div className="space-y-2">
            {epic.items.map((item) => (
              <ItemRow key={item.id} item={item} level={0} onItemClick={onItemClick} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ItemRow({ item, level, onItemClick }: { item: HierarchyItem; level: number; onItemClick?: (item: HierarchyItem) => void }) {
  const [expanded, setExpanded] = React.useState(false);
  const hasChildren = item.children && item.children.length > 0;

  return (
    <div className="space-y-2">
      <div
        className={`flex items-center gap-2 py-2 px-3 hover:bg-muted/50 rounded-lg cursor-pointer transition ${
          level > 0 ? `ml-${level * 6}` : ""
        }`}
        onClick={() => {
          if (hasChildren) {
            setExpanded(!expanded);
          } else if (onItemClick) {
            onItemClick(item);
          }
        }}
      >
        {hasChildren && (
          <button className="h-6 w-6 flex items-center justify-center">
            {expanded ? "▼" : "▶"}
          </button>
        )}
        {!hasChildren && <div className="w-6" />}

        <div
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: getItemTypeColor(item.item_type) }}
        />

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{item.title || "Sem título"}</p>
        </div>

        <div className="flex items-center gap-2">
          {item.item_type && (
            <Badge variant="secondary" className="text-xs">
              {item.item_type}
            </Badge>
          )}
          {item.status && (
            <Badge variant="outline" className="text-xs">
              {item.status}
            </Badge>
          )}
        </div>
      </div>

      {hasChildren && expanded && (
        <div className="space-y-2">
          {item.children.map((child) => (
            <ItemRow key={child.id} item={child} level={level + 1} onItemClick={onItemClick} />
          ))}
        </div>
      )}
    </div>
  );
}

// Need to import React for useState
import * as React from "react";
