function App() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-slate-50">
      <section className="mx-auto flex max-w-5xl flex-col gap-8 rounded-3xl border border-white/10 bg-white/5 p-10 shadow-2xl shadow-slate-950/40 backdrop-blur">
        <span className="w-fit rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-1 text-sm font-medium text-emerald-200">
          Tailwind v4 Ready
        </span>
        <div className="space-y-4">
          <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Frontend baseline is now wired for utility-first styling.
          </h1>
          <p className="max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
            Vite is using the official Tailwind CSS Vite plugin, and this screen is rendered
            entirely with Tailwind utility classes.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <article className="rounded-2xl border border-white/10 bg-slate-900/80 p-5">
            <p className="text-sm text-slate-400">Plugin</p>
            <strong className="mt-2 block text-lg text-white">@tailwindcss/vite</strong>
          </article>
          <article className="rounded-2xl border border-white/10 bg-slate-900/80 p-5">
            <p className="text-sm text-slate-400">CSS entry</p>
            <strong className="mt-2 block text-lg text-white">@import "tailwindcss"</strong>
          </article>
          <article className="rounded-2xl border border-white/10 bg-slate-900/80 p-5">
            <p className="text-sm text-slate-400">Status</p>
            <strong className="mt-2 block text-lg text-emerald-300">Applied</strong>
          </article>
        </div>
      </section>
    </main>
  )
}

export default App
