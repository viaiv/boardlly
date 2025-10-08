import { useState, useEffect } from "react";
import { useProject } from "@/lib/project";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Loader2, ChevronRight, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  getProjectHierarchy,
  countByType,
  type HierarchyResponse,
  type HierarchyItem,
  type HierarchyEpic,
} from "@/lib/hierarchy";

export function Hierarchy() {
  const { activeProject } = useProject();
  const [hierarchy, setHierarchy] = useState<HierarchyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadHierarchy();
  }, [activeProject?.id]);

  async function loadHierarchy() {
    if (!activeProject?.id) return;

    try {
      setLoading(true);
      const data = await getProjectHierarchy(activeProject.id);
      setHierarchy(data);

      // Auto-expand first level
      const firstLevelIds = new Set<number>();
      data.epics.forEach((epic) => {
        epic.items.forEach((item) => firstLevelIds.add(item.id));
      });
      data.orphans.forEach((item) => firstLevelIds.add(item.id));
      setExpandedItems(firstLevelIds);
    } catch (error) {
      toast.error("Erro ao carregar hierarquia", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setLoading(false);
    }
  }

  function toggleExpand(itemId: number) {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  }

  function getItemTypeColor(type: string | null): string {
    switch (type) {
      case "story":
        return "bg-blue-500";
      case "task":
        return "bg-green-500";
      case "feature":
        return "bg-purple-500";
      case "bug":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  }

  function renderItem(item: HierarchyItem, level: number = 0) {
    const isExpanded = expandedItems.has(item.id);
    const hasChildren = item.children && item.children.length > 0;

    return (
      <div key={item.id} className="space-y-1">
        <div
          className={`flex items-center gap-2 py-2 px-3 hover:bg-muted/50 rounded-lg ${
            level > 0 ? "ml-" + level * 6 : ""
          }`}
        >
          {hasChildren ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => toggleExpand(item.id)}
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>
          ) : (
            <div className="w-6" />
          )}

          <div className={`w-2 h-2 rounded-full ${getItemTypeColor(item.item_type)}`} />

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

        {hasChildren && isExpanded && (
          <div className="space-y-1">
            {item.children.map((child) => renderItem(child, level + 1))}
          </div>
        )}
      </div>
    );
  }

  function renderEpic(epic: HierarchyEpic) {
    return (
      <Card key={epic.epic_option_id || "no-epic"}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-lg">📦</span>
            {epic.epic_name || "Sem Épico"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {epic.items.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum item neste épico</p>
          ) : (
            epic.items.map((item) => renderItem(item))
          )}
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!hierarchy) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Nenhuma hierarquia encontrada</p>
      </div>
    );
  }

  const stats = countByType(hierarchy);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Hierarquia do Projeto</h1>
          <p className="text-muted-foreground">
            Visualização épico → história → tarefa
          </p>
        </div>
        <Button onClick={loadHierarchy} variant="outline">
          Atualizar
        </Button>
      </div>

      {/* Statistics */}
      <div className="grid gap-4 md:grid-cols-4">
        {Object.entries(stats).map(([type, count]) => (
          <Card key={type}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{count}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Epics */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Épicos</h2>
        {hierarchy.epics.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                Nenhum épico cadastrado. Items sem épico aparecem em "Outros" abaixo.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {hierarchy.epics.map((epic) => renderEpic(epic))}
          </div>
        )}
      </div>

      {/* Orphans */}
      {hierarchy.orphans.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Outros (sem épico)</h2>
          <Card>
            <CardContent className="pt-6 space-y-1">
              {hierarchy.orphans.map((item) => renderItem(item))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
