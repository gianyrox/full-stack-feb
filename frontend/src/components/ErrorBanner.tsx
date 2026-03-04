export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
      <div className="font-semibold">Something went wrong</div>
      <div className="mt-1 whitespace-pre-wrap">{message}</div>
    </div>
  );
}
