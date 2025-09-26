export function Overview() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Visão Geral</h1>
        <p className="text-sm text-muted-foreground">
          KPIs e gráficos principais do Project conectados ao GitHub.
        </p>
      </header>
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Cards e gráficos serão implementados após a alimentação da API.
      </div>
    </div>
  );
}
