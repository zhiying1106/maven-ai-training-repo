import Chat from "@/components/Chat";

export default function Home() {
  return (
    <main className="mx-auto flex h-full min-h-screen w-full max-w-3xl flex-col px-4 py-6 sm:px-6 sm:py-10">
      <header className="mb-6 shrink-0 space-y-1 text-center sm:mb-8">
        <p className="text-sm font-medium uppercase tracking-wider text-coach-accent">
          Mindful Coach
        </p>
        <h1 className="text-2xl font-semibold text-coach-text sm:text-3xl">
          Your supportive mental coach
        </h1>
        <p className="mx-auto max-w-md text-sm text-coach-muted sm:text-base">
          A calm space to talk through stress, build habits, and find motivation.
        </p>
      </header>

      <Chat />
    </main>
  );
}
