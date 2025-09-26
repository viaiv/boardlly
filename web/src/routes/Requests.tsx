import { Button } from "@/components/ui/button";

export function Requests() {
  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Solicitações</h1>
          <p className="text-sm text-muted-foreground">
            Abra solicitações para mudanças e acompanhe o status.
          </p>
        </div>
        <Button>Nova Solicitação</Button>
      </header>
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Listagem e filtros serão implementados com a API de solicitações.
      </div>
    </div>
  );
}
