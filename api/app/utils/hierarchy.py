"""
Utilities for working with project item hierarchy.

Handles derivation of item types from labels, title patterns, and other metadata.
"""


def derive_item_type_from_labels(labels: list[str] | None, title: str | None = None) -> str | None:
    """
    Deriva o tipo de item a partir de labels e título.

    Prioridade de detecção:
    1. Labels: type:story, type:task, type:feature, type:bug
    2. Prefixo no título: "HISTORY:" indica história

    Args:
        labels: Lista de labels do item (ex: ["type:story", "priority:high"])
        title: Título do item (opcional, para detecção via prefixo)

    Returns:
        str | None: O tipo detectado ("story", "task", "feature", "bug") ou None se não detectado

    Examples:
        >>> derive_item_type_from_labels(["type:story", "priority:high"])
        'story'

        >>> derive_item_type_from_labels(["type:task"])
        'task'

        >>> derive_item_type_from_labels([], "HISTORY: User Login")
        'story'

        >>> derive_item_type_from_labels(None)
        None
    """
    if not labels:
        labels = []

    # Map de type labels para item types
    type_label_mapping = {
        "type:story": "story",
        "type:task": "task",
        "type:feature": "feature",
        "type:bug": "bug",
    }

    # Procurar por type labels
    for label in labels:
        label_lower = label.lower().strip()
        if label_lower in type_label_mapping:
            return type_label_mapping[label_lower]

    # Se não encontrou via labels, verificar título
    if title:
        title_upper = title.upper().strip()
        if title_upper.startswith("HISTORY:"):
            return "story"

    return None


def is_story(labels: list[str] | None, title: str | None = None) -> bool:
    """
    Verifica se um item é uma história (story).

    Args:
        labels: Lista de labels do item
        title: Título do item (opcional)

    Returns:
        bool: True se for história, False caso contrário
    """
    return derive_item_type_from_labels(labels, title) == "story"


def is_task(labels: list[str] | None) -> bool:
    """
    Verifica se um item é uma tarefa (task).

    Args:
        labels: Lista de labels do item

    Returns:
        bool: True se for tarefa, False caso contrário
    """
    return derive_item_type_from_labels(labels) == "task"


def get_hierarchy_level(item_type: str | None) -> int:
    """
    Retorna o nível hierárquico de um tipo de item.

    Níveis:
    - 0: Epic (campo separado, não um item)
    - 1: Story (história)
    - 2: Task/Feature/Bug (tarefas em geral)

    Args:
        item_type: Tipo do item ("story", "task", "feature", "bug")

    Returns:
        int: Nível hierárquico (1 para story, 2 para outros, 99 para desconhecido)
    """
    if item_type == "story":
        return 1
    elif item_type in ("task", "feature", "bug"):
        return 2
    else:
        return 99  # Unknown/undefined type
