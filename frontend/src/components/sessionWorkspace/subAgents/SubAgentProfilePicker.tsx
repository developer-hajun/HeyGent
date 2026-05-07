import { useMemo, useState } from 'react'
import { Input } from '@/components/ui/input'
import { SUB_AGENT_PROFILE_IMAGE_OPTIONS, type SubAgentSpriteId } from './subAgentOptions'

export function SubAgentProfilePicker({
  onChange,
  value,
}: {
  onChange: (spriteId: SubAgentSpriteId) => void
  value: SubAgentSpriteId
}) {
  const [search, setSearch] = useState('')
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (query === '') return SUB_AGENT_PROFILE_IMAGE_OPTIONS
    return SUB_AGENT_PROFILE_IMAGE_OPTIONS.filter((option) =>
      option.label.toLowerCase().includes(query),
    )
  }, [search])

  return (
    <>
      <Input
        placeholder="Search profiles..."
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        className="mb-2 h-8 text-sm"
        autoFocus
      />
      <div className="grid max-h-60 grid-cols-5 gap-2 overflow-y-auto">
        {filtered.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => {
              onChange(option.id)
              setSearch('')
            }}
            className={`hover:bg-accent flex h-12 w-12 items-center justify-center rounded transition-colors ${
              value === option.id ? 'bg-accent ring-primary ring-1' : ''
            }`}
            title={option.label}
            aria-label={`${option.label} 선택`}
          >
            <img src={option.src} alt="" className="h-10 w-10 object-contain" draggable={false} />
          </button>
        ))}
        {filtered.length === 0 && (
          <p className="text-muted-foreground col-span-5 py-2 text-center text-xs">
            No profiles match
          </p>
        )}
      </div>
    </>
  )
}
