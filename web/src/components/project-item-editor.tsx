import { FormEvent, ReactNode, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import {
  classifyProjectItem,
  classificationBadgeClass,
  formatDateDisplay,
  formatDateForInput,
  type ProjectItem,
  type ProjectItemComment,
  type ProjectItemDetails,
} from "@/lib/project-items";
import { cn } from "@/lib/utils";

export interface ProjectItemEditorValues {
  startDate: string | null;
  endDate: string | null;
  dueDate: string | null;
}

interface ProjectItemEditorProps {
  item: ProjectItem | null;
  open: boolean;
  canEdit: boolean;
  onClose: () => void;
  onSubmit: (values: ProjectItemEditorValues) => Promise<void>;
  submitting: boolean;
  details: ProjectItemDetails | null;
  detailsLoading: boolean;
  detailsError: string | null;
  comments: ProjectItemComment[];
  commentsLoading: boolean;
  commentsError: string | null;
  onRefresh?: () => void;
}

export function ProjectItemEditor({
  item,
  open,
  canEdit,
  onClose,
  onSubmit,
  submitting,
  details,
  detailsLoading,
  detailsError,
  comments,
  commentsLoading,
  commentsError,
  onRefresh,
}: ProjectItemEditorProps) {
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [dueDate, setDueDate] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!item) {
      setStartDate("");
      setEndDate("");
      setDueDate("");
      setError(null);
      return;
    }
    setStartDate(formatDateForInput(item.start_date) ?? "");
    setEndDate(formatDateForInput(item.end_date) ?? "");
    setDueDate(formatDateForInput(item.due_date) ?? "");
    setError(null);
  }, [item]);

  if (!item) {
    return null;
  }

  const classification = classifyProjectItem(item);
  const detail = details;
  const baseTitle = item.title?.trim().length ? item.title.trim() : "Sem título";
  const detailTitle = detail?.title && detail.title.trim().length ? detail.title.trim() : null;
  const displayTitle = detailTitle ?? baseTitle;
  const remoteUpdated = item.remote_updated_at ? new Date(item.remote_updated_at) : null;
  const iterationStart = formatDateDisplay(item.iteration_start);
  const iterationEnd = formatDateDisplay(item.iteration_end);
  const startDisplay = formatDateDisplay(item.start_date);
  const endDisplay = formatDateDisplay(item.end_date);
  const dueDisplay = formatDateDisplay(item.due_date);
  const itemUpdatedDisplay = formatDateDisplay(item.updated_at);
  const sortedFieldEntries = item.field_values
    ? Object.entries(item.field_values).sort((a, b) => a[0].localeCompare(b[0], "pt", { sensitivity: "base" }))
    : [];
  const detailLabels = detail?.labels ?? [];
  const description = detail?.body_text ?? detail?.body ?? null;
  const detailState = detail?.state ?? null;
  const detailNumber = detail?.number ?? null;
  const detailAuthor = detail?.author;
  const detailCreated = formatDateDisplay(detail?.created_at);
  const detailUpdated = formatDateDisplay(detail?.updated_at);
  const detailUrl = detail?.url ?? item.url;
  const detailMerged = detail?.merged;
  const remoteUpdatedLabel = detailUpdated ?? (remoteUpdated ? remoteUpdated.toLocaleString() : null);
  const epicName = item.epic_name ?? classification.epicName;
  const showMissingEpic = !epicName && classification.accent !== "epic";
  const sortedComments = comments
    .slice()
    .sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : Number.MAX_SAFE_INTEGER;
      const bTime = b.created_at ? new Date(b.created_at).getTime() : Number.MAX_SAFE_INTEGER;
      return aTime - bTime;
    });

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!canEdit) {
      onClose();
      return;
    }
    try {
      await onSubmit({
        startDate: startDate || null,
        endDate: endDate || null,
        dueDate: dueDate || null,
      });
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Não foi possível salvar as alterações";
      setError(message);
    }
  };

  const modalDescription = canEdit
    ? "Atualize datas importantes deste item. As mudanças serão refletidas no GitHub."
    : "Visualize os dados sincronizados do GitHub. Apenas owners ou admins podem editar.";

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={displayTitle}
      description={modalDescription}
      size="xl"
      footer={
        canEdit ? (
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={onClose} disabled={submitting}>
              Cancelar
            </Button>
            <Button type="submit" form="project-item-editor-form" disabled={submitting}>
              {submitting ? "Salvando..." : "Salvar"}
            </Button>
          </div>
        ) : (
          <Button variant="outline" onClick={onClose}>
            Fechar
          </Button>
        )
      }
    >
      <form id="project-item-editor-form" className="space-y-6" onSubmit={handleSubmit}>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 font-semibold uppercase",
              classificationBadgeClass(classification.accent),
            )}
          >
            {classification.typeLabel}
          </span>
          {epicName ? (
            <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 font-medium text-muted-foreground">
              Épico: {epicName}
            </span>
          ) : null}
          {showMissingEpic ? (
            <span className="inline-flex items-center rounded-full border border-amber-500 bg-amber-100 px-2 py-0.5 font-medium text-amber-700">
              Sem épico vinculado
            </span>
          ) : null}
          {item.status ? (
            <span className="rounded-full bg-muted px-2 py-0.5 font-medium text-muted-foreground">
              Status: {item.status}
            </span>
          ) : null}
        </div>

        <div className="grid gap-4">
          <div className="space-y-2">
            <Label htmlFor="start-date">Data de início</Label>
            <div className="flex items-center gap-2">
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                disabled={!canEdit || submitting}
              />
              {startDate ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setStartDate("")}
                  disabled={!canEdit || submitting}
                >
                  Limpar
                </Button>
              ) : null}
            </div>
            {startDisplay ? <p className="text-[11px] text-muted-foreground">Atual: {startDisplay}</p> : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="end-date">Data de término</Label>
            <div className="flex items-center gap-2">
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                disabled={!canEdit || submitting}
              />
              {endDate ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setEndDate("")}
                  disabled={!canEdit || submitting}
                >
                  Limpar
                </Button>
              ) : null}
            </div>
            {endDisplay ? <p className="text-[11px] text-muted-foreground">Atual: {endDisplay}</p> : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="due-date">Data de entrega</Label>
            <div className="flex items-center gap-2">
              <Input
                id="due-date"
                type="date"
                value={dueDate}
                onChange={(event) => setDueDate(event.target.value)}
                disabled={!canEdit || submitting}
              />
              {dueDate ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setDueDate("")}
                  disabled={!canEdit || submitting}
                >
                  Limpar
                </Button>
              ) : null}
            </div>
            {dueDisplay ? <p className="text-[11px] text-muted-foreground">Atual: {dueDisplay}</p> : null}
          </div>
        </div>

        {remoteUpdatedLabel ? (
          <p className="text-xs text-muted-foreground">Última atualização remota: {remoteUpdatedLabel}</p>
        ) : null}

        {!canEdit ? (
          <p className="rounded-md border border-border/60 bg-muted/40 p-2 text-xs text-muted-foreground">
            Você não possui permissão para editar este item, mas pode visualizar os dados sincronizados do GitHub.
          </p>
        ) : null}

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground">Detalhes do GitHub</h3>
            {onRefresh ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onRefresh}
                disabled={detailsLoading || commentsLoading || submitting}
              >
                Atualizar
              </Button>
            ) : null}
          </div>

          {detailsLoading ? (
            <p className="text-xs text-muted-foreground">Carregando detalhes...</p>
          ) : null}

          {detailsError ? (
            <p className="rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-600">{detailsError}</p>
          ) : null}

          {!detailsLoading && !detailsError ? (
            <>
              {description ? (
                <div className="rounded-md border border-border/60 bg-muted/30 p-3 text-sm text-foreground whitespace-pre-wrap">
                  {description}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">Nenhuma descrição disponível.</p>
              )}

              <dl className="grid gap-2 text-sm">
                {detailNumber !== null ? <DetailRow label="Número" value={`#${detailNumber}`} /> : null}
                <DetailRow label="Tipo" value={detail?.content_type ?? item.content_type ?? "—"} />
                <DetailRow label="Estado" value={detailState ?? item.status ?? "—"} />
                {detailMerged !== null ? <DetailRow label="Mergeado" value={detailMerged ? "Sim" : "Não"} /> : null}
                <DetailRow
                  label="Épico"
                  value={
                    epicName
                      ? epicName
                      : classification.accent === "epic"
                        ? "Este item é um épico"
                        : (
                          <span className="font-medium text-amber-600">Sem épico vinculado</span>
                        )
                  }
                />
                <DetailRow
                  label="Autor"
                  value={
                    detailAuthor?.login ? (
                      detailAuthor.url ? (
                        <a
                          href={detailAuthor.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary underline"
                        >
                          {detailAuthor.login}
                        </a>
                      ) : (
                        detailAuthor.login
                      )
                    ) : (
                      "—"
                    )
                  }
                />
                <DetailRow label="Criado em" value={detailCreated ?? "—"} />
                <DetailRow label="Atualizado em" value={detailUpdated ?? itemUpdatedDisplay ?? "—"} />
                <DetailRow label="Assignees" value={item.assignees?.length ? item.assignees.join(", ") : "Nenhum"} />
                <DetailRow label="Iteração" value={item.iteration ?? "—"} />
                <DetailRow label="Início da Iteração" value={iterationStart ?? "—"} />
                <DetailRow label="Fim da Iteração" value={iterationEnd ?? "—"} />
                <DetailRow label="Estimate" value={item.estimate ?? "—"} />
                <DetailRow label="Início" value={startDisplay ?? "—"} />
                <DetailRow label="Término" value={endDisplay ?? "—"} />
                <DetailRow label="Entrega" value={dueDisplay ?? "—"} />
                <DetailRow
                  label="Link"
                  value={
                    detailUrl ? (
                      <a href={detailUrl} target="_blank" rel="noreferrer" className="text-primary underline">
                        Abrir no GitHub
                      </a>
                    ) : (
                      "—"
                    )
                  }
                />
              </dl>

              {detailLabels.length ? (
                <div className="flex flex-wrap gap-2">
                  {detailLabels.map((label) => (
                    <span
                      key={label.name}
                      className="rounded-full border border-border/60 px-2 py-0.5 text-xs"
                      style={
                        label.color
                          ? {
                              backgroundColor: `#${label.color}20`,
                              borderColor: `#${label.color}`,
                              color: `#${label.color}`,
                            }
                          : undefined
                      }
                    >
                      {label.name}
                    </span>
                  ))}
                </div>
              ) : null}
            </>
          ) : null}

          {sortedFieldEntries.length ? (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase text-muted-foreground">Campos sincronizados</h4>
              <dl className="grid gap-1 text-xs">
                {sortedFieldEntries.map(([key, value]) => (
                  <DetailRow
                    key={key}
                    label={key}
                    value={typeof value === "object" ? JSON.stringify(value) : String(value ?? "—")}
                  />
                ))}
              </dl>
            </div>
          ) : null}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground">Comentários ({sortedComments.length})</h3>
          </div>

          {commentsLoading ? (
            <p className="text-xs text-muted-foreground">Carregando comentários...</p>
          ) : null}

          {commentsError ? (
            <p className="rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-600">{commentsError}</p>
          ) : null}

          {!commentsLoading && !commentsError ? (
            sortedComments.length ? (
              <ul className="max-h-60 space-y-2 overflow-y-auto pr-1 text-sm">
                {sortedComments.map((comment) => (
                  <li key={comment.id}>
                    <details className="group rounded-md border border-border/60 bg-muted/20 p-3">
                      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[11px] font-semibold uppercase text-muted-foreground transition group-open:text-foreground">
                        <span>{comment.author ?? "Usuário desconhecido"}</span>
                        <span>{formatDateDisplay(comment.created_at) ?? "—"}</span>
                      </summary>
                      <div className="mt-3 space-y-2 border-t border-border/60 pt-3">
                        <p className="whitespace-pre-line text-sm text-foreground">{comment.body}</p>
                        {comment.url ? (
                          <a
                            href={comment.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex text-xs font-medium text-primary underline"
                          >
                            Ver no GitHub
                          </a>
                        ) : null}
                      </div>
                    </details>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">Nenhum comentário encontrado neste item.</p>
            )
          ) : null}
        </section>

        {error ? (
          <p className="rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-600">{error}</p>
        ) : null}
      </form>
    </Modal>
  );
}

function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] items-start gap-x-4 gap-y-1">
      <dt className="text-xs font-medium uppercase text-muted-foreground">{label}</dt>
      <dd className="text-sm text-foreground">{value ?? "—"}</dd>
    </div>
  );
}
