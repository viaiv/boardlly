export function Backlog() {
  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Backlog</h1>
          <p className="text-sm text-muted-foreground">
            Itens internos e integração opcional com Issues do GitHub.
          </p>
        </div>
      </header>
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        A lista de backlog será alimentada pela API.
      </div>
    </div>
  );
}
