import { useState, useEffect } from "react";
import { useProject } from "@/lib/project";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";
import { Loader2, RefreshCw, ExternalLink } from "lucide-react";
import {
  listEpics,
  type EpicOption,
} from "@/lib/epics";

export function Epics() {
  const { activeProject } = useProject();
  const [epics, setEpics] = useState<EpicOption[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEpics();
  }, [activeProject?.id]);

  async function loadEpics() {
    try {
      setLoading(true);
      const data = await listEpics();
      setEpics(data);
    } catch (error) {
      toast.error("Erro ao carregar épicos", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setLoading(false);
    }
  }


  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Épicos</h1>
          <p className="text-muted-foreground">
            Visualize os épicos sincronizados do GitHub Projects
          </p>
        </div>
        <Button onClick={loadEpics} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          Atualizar
        </Button>
      </div>

      <Card className="border-blue-200 bg-blue-50/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <ExternalLink className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-blue-900">
                Gerenciar Épicos no GitHub Projects
              </p>
              <p className="text-sm text-blue-700">
                Para adicionar, editar ou remover épicos, acesse seu projeto no GitHub Projects V2
                e gerencie as opções do campo "Epic". As mudanças serão sincronizadas automaticamente.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {epics.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground text-center">
              Nenhum épico encontrado no projeto.
              <br />
              Configure o campo "Epic" no seu GitHub Project para começar.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {epics.map((epic) => (
            <Card key={epic.id}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  {epic.color && (
                    <div
                      className="w-4 h-4 rounded-full border border-gray-200"
                      style={{ backgroundColor: epic.color }}
                    />
                  )}
                  <CardTitle className="text-lg">{epic.name}</CardTitle>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
