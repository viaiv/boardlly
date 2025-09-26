import { useMemo } from "react";

export interface AvatarProps {
  text: string;
}

export function Avatar({ text }: AvatarProps) {
  const initials = useMemo(
    () =>
      text
        .split(" ")
        .filter(Boolean)
        .map((word) => word[0]?.toUpperCase())
        .join("")
        .slice(0, 2),
    [text],
  );

  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-foreground">
      {initials || "?"}
    </div>
  );
}
