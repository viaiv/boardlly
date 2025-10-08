import { useProject } from "@/lib/project";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function ProjectSwitcher() {
  const { projects, activeProject, setActiveProject, status } = useProject();

  if (status === "loading") {
    return (
      <div className="flex h-10 w-[200px] items-center justify-center rounded-md border border-input bg-background px-3 text-sm text-muted-foreground">
        Carregando...
      </div>
    );
  }

  if (status === "error" || projects.length === 0) {
    return (
      <div className="flex h-10 w-[200px] items-center justify-center rounded-md border border-input bg-background px-3 text-sm text-muted-foreground">
        Nenhum projeto
      </div>
    );
  }

  return (
    <Select
      value={activeProject?.id.toString()}
      onValueChange={(value) => setActiveProject(parseInt(value, 10))}
    >
      <SelectTrigger className="w-[200px]">
        <SelectValue placeholder="Selecione um projeto" />
      </SelectTrigger>
      <SelectContent>
        {projects.map((project) => (
          <SelectItem key={project.id} value={project.id.toString()}>
            {project.name || `${project.owner_login}/${project.project_number}`}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
