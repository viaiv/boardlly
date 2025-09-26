import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";
import { useSession } from "@/lib/session";

export function AccountSetup() {
  const navigate = useNavigate();
  const { refresh, user } = useSession();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user && !user.needsAccountSetup) {
      navigate("/", { replace: true });
    }
  }, [user, navigate]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Informe um nome válido para a conta.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await apiFetch("/api/accounts", {
        method: "POST",
        body: JSON.stringify({ name: name.trim() }),
      });
      await refresh();
      navigate("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Não foi possível criar a conta";
      setError(message);
      setIsSubmitting(false);
    }
  };

  if (!user?.needsAccountSetup) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6 py-12">
      <div className="w-full max-w-lg space-y-6">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">Configurar conta</h1>
          <p className="text-sm text-muted-foreground">
            Olá {user?.name || user?.email}, escolha um nome para sua conta/organização.
          </p>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="accountName">Nome da conta</Label>
            <Input
              id="accountName"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Equipe Tactyo"
              required
            />
          </div>
          {error ? <p className="text-sm text-red-500">{error}</p> : null}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Criando..." : "Criar conta"}
          </Button>
        </form>
      </div>
    </div>
  );
}
