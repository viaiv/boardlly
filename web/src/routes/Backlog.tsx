import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { SearchIcon, ExternalLinkIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiFetch } from "@/lib/api";

type ProjectItem = {
  id: number;
  title: string;
  status: string | null;
  epic: string | null;
  iteration: string | null;
  estimate: number | null;
  assignees: string[];
  url: string | null;
  content_type: string | null;
  content_node_id: string | null;
  updated_at: string;
};

export function Backlog() {
  const [items, setItems] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtros
  const [statusFilter, setStatusFilter] = useState<string>("backlog");
  const [epicFilter, setEpicFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Epics disponíveis (extraídos dos items)
  const [availableEpics, setAvailableEpics] = useState<string[]>([]);

  useEffect(() => {
    loadItems();
  }, [statusFilter]);

  async function loadItems() {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();

      // Filtro de status: backlog ou todo
      if (statusFilter === "backlog") {
        params.append("status", "Backlog");
      } else if (statusFilter === "todo") {
        params.append("status", "Todo");
      } else if (statusFilter === "all") {
        // Não filtrar por status
      }

      const data = await apiFetch<ProjectItem[]>(`/api/projects/current/items?${params}`);

      // Filtrar items sem iteration (backlog)
      const backlogItems = data.filter((item) => !item.iteration || statusFilter === "all");

      setItems(backlogItems);

      // Extrair epics únicos
      const epics = Array.from(new Set(backlogItems.map((item) => item.epic).filter(Boolean)));
      setAvailableEpics(epics as string[]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erro ao carregar backlog";
      setError(errorMessage);
      toast.error("Erro ao carregar backlog", {
        description: errorMessage,
      });
    } finally {
      setLoading(false);
    }
  }

  function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(date);
  }

  // Filtrar items no frontend
  const filteredItems = items.filter((item) => {
    // Filtro de epic
    if (epicFilter !== "all" && item.epic !== epicFilter) {
      return false;
    }

    // Filtro de busca
    if (searchQuery && !item.title.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }

    return true;
  });

  // Agrupar por epic
  const groupedByEpic: Record<string, ProjectItem[]> = {};
  const itemsWithoutEpic: ProjectItem[] = [];

  filteredItems.forEach((item) => {
    if (item.epic) {
      if (!groupedByEpic[item.epic]) {
        groupedByEpic[item.epic] = [];
      }
      groupedByEpic[item.epic].push(item);
    } else {
      itemsWithoutEpic.push(item);
    }
  });

  const getItemTypeLabel = (type: string | null) => {
    if (type === "Issue") return "Issue";
    if (type === "PullRequest") return "PR";
    if (type === "DraftIssue") return "Draft";
    return "Item";
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Backlog</h1>
        <p className="text-sm text-muted-foreground">
          Itens do projeto que ainda não foram agendados para uma sprint
        </p>
      </header>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3">
        {/* Filtro de status */}
        <div className="flex gap-2">
          <Button
            variant={statusFilter === "backlog" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("backlog")}
          >
            Backlog
          </Button>
          <Button
            variant={statusFilter === "todo" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("todo")}
          >
            Todo
          </Button>
          <Button
            variant={statusFilter === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("all")}
          >
            Todos
          </Button>
        </div>

        {/* Filtro de epic */}
        {availableEpics.length > 0 && (
          <Select value={epicFilter} onValueChange={setEpicFilter}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Filtrar por Epic" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os Epics</SelectItem>
              {availableEpics.map((epic) => (
                <SelectItem key={epic} value={epic}>
                  {epic}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {/* Busca */}
        <div className="relative flex-1 max-w-sm">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Buscar itens..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="p-4 border rounded-lg">
              <div className="space-y-2">
                <Skeleton className="h-5 w-3/4" />
                <div className="flex gap-2">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-24" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Erro */}
      {error && !loading && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Vazio */}
      {!loading && !error && filteredItems.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <p className="text-sm text-muted-foreground mb-4">
            {items.length === 0
              ? "Nenhum item no backlog. Todos os itens estão em sprints!"
              : "Nenhum item encontrado com os filtros selecionados"}
          </p>
          {items.length === 0 && (
            <Link to="/roadmap">
              <Button variant="outline">Ver Roadmap</Button>
            </Link>
          )}
        </div>
      )}

      {/* Lista agrupada */}
      {!loading && !error && filteredItems.length > 0 && (
        <div className="space-y-8">
          {/* Itens sem epic */}
          {itemsWithoutEpic.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-muted-foreground">Sem Epic</h2>
              <div className="space-y-2">
                {itemsWithoutEpic.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 border rounded-lg hover:bg-accent transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-medium truncate">{item.title}</h3>
                          {item.url && (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-muted-foreground hover:text-foreground"
                            >
                              <ExternalLinkIcon className="h-4 w-4" />
                            </a>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                          <Badge variant="outline">{getItemTypeLabel(item.content_type)}</Badge>
                          {item.status && <Badge variant="secondary">{item.status}</Badge>}
                          {item.estimate && (
                            <Badge variant="outline">{item.estimate} pts</Badge>
                          )}
                          {item.assignees.length > 0 && (
                            <span>👤 {item.assignees.join(", ")}</span>
                          )}
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDate(item.updated_at)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Itens agrupados por epic */}
          {Object.entries(groupedByEpic).map(([epic, epicItems]) => (
            <div key={epic} className="space-y-3">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold">{epic}</h2>
                <Badge variant="outline">{epicItems.length} items</Badge>
              </div>
              <div className="space-y-2">
                {epicItems.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 border rounded-lg hover:bg-accent transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-medium truncate">{item.title}</h3>
                          {item.url && (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-muted-foreground hover:text-foreground"
                            >
                              <ExternalLinkIcon className="h-4 w-4" />
                            </a>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                          <Badge variant="outline">{getItemTypeLabel(item.content_type)}</Badge>
                          {item.status && <Badge variant="secondary">{item.status}</Badge>}
                          {item.estimate && (
                            <Badge variant="outline">{item.estimate} pts</Badge>
                          )}
                          {item.assignees.length > 0 && (
                            <span>👤 {item.assignees.join(", ")}</span>
                          )}
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDate(item.updated_at)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
