type Props = {
  variant?: "neutral" | "success" | "warning" | "error" | "info";
  children: React.ReactNode;
};

const variantClasses: Record<NonNullable<Props["variant"]>, string> = {
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
  success: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  warning: "bg-amber-100 text-amber-800 ring-amber-200",
  error: "bg-rose-100 text-rose-800 ring-rose-200",
  info: "bg-sky-100 text-sky-800 ring-sky-200",
};

export function Badge({ variant = "neutral", children }: Props) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        variantClasses[variant],
      ].join(" ")}
    >
      {children}
    </span>
  );
}
