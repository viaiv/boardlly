import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiFetch } from "@/lib/api";

type ChangeRequestCreate = {
  title: string;
  description?: string;
  impact?: string;
  priority: string;
  request_type?: string;
};

export function RequestNew() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<ChangeRequestCreate>({
    title: "",
    description: "",
    impact: "",
    priority: "medium",
    request_type: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Remover campos vazios opcionais
      const payload: ChangeRequestCreate = {
        title: formData.title,
        priority: formData.priority,
      };

      if (formData.description?.trim()) {
        payload.description = formData.description;
      }
      if (formData.impact?.trim()) {
        payload.impact = formData.impact;
      }
      if (formData.request_type) {
        payload.request_type = formData.request_type;
      }

      const response = await apiFetch<{ id: string }>("/api/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      // Redirecionar para a página de detalhes
      navigate(`/requests/${response.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar solicitação");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Nova Solicitação</h1>
        <p className="text-sm text-muted-foreground">
          Proponha uma mudança, melhoria ou correção para o projeto
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Título */}
        <div className="space-y-2">
          <Label htmlFor="title">
            Título <span className="text-destructive">*</span>
          </Label>
          <Input
            id="title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="Ex: Adicionar filtro por data no relatório"
            required
            minLength={3}
            maxLength={500}
          />
          <p className="text-xs text-muted-foreground">
            Resumo claro e objetivo da solicitação
          </p>
        </div>

        {/* Descrição */}
        <div className="space-y-2">
          <Label htmlFor="description">Descrição</Label>
          <Textarea
            id="description"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Descreva em detalhes o que está sendo solicitado..."
            rows={5}
          />
          <p className="text-xs text-muted-foreground">
            Explique o contexto, motivação e detalhes da solicitação
          </p>
        </div>

        {/* Impacto */}
        <div className="space-y-2">
          <Label htmlFor="impact">Impacto Esperado</Label>
          <Textarea
            id="impact"
            value={formData.impact}
            onChange={(e) => setFormData({ ...formData, impact: e.target.value })}
            placeholder="Qual o benefício esperado? Quem será impactado?"
            rows={3}
          />
          <p className="text-xs text-muted-foreground">
            Descreva os benefícios e impactos positivos esperados
          </p>
        </div>

        {/* Tipo e Prioridade (lado a lado) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Tipo */}
          <div className="space-y-2">
            <Label htmlFor="request_type">Tipo</Label>
            <Select
              value={formData.request_type}
              onValueChange={(value) =>
                setFormData({ ...formData, request_type: value })
              }
            >
              <SelectTrigger id="request_type">
                <SelectValue placeholder="Selecione o tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="feature">Nova Funcionalidade</SelectItem>
                <SelectItem value="bug">Correção de Bug</SelectItem>
                <SelectItem value="tech_debt">Dívida Técnica</SelectItem>
                <SelectItem value="docs">Documentação</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Prioridade */}
          <div className="space-y-2">
            <Label htmlFor="priority">
              Prioridade <span className="text-destructive">*</span>
            </Label>
            <Select
              value={formData.priority}
              onValueChange={(value) => setFormData({ ...formData, priority: value })}
              required
            >
              <SelectTrigger id="priority">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Baixa</SelectItem>
                <SelectItem value="medium">Média</SelectItem>
                <SelectItem value="high">Alta</SelectItem>
                <SelectItem value="urgent">Urgente</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Ações */}
        <div className="flex gap-3 pt-4">
          <Button type="submit" disabled={loading}>
            {loading ? "Criando..." : "Criar Solicitação"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/requests")}
            disabled={loading}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </div>
  );
}
