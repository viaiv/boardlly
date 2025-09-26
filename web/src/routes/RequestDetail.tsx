import { useParams } from "react-router-dom";

export function RequestDetail() {
  const { requestId } = useParams<{ requestId: string }>();

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Solicitação #{requestId}</h1>
        <p className="text-sm text-muted-foreground">
          Detalhes, comentários e ações de aprovação/rejeição.
        </p>
      </header>
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Conteúdo será conectado à API de solicitações.
      </div>
    </div>
  );
}
