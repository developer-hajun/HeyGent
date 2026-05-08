import { Checkbox } from '@/components/ui/checkbox'
import { SUB_AGENT_SKILLS, type SubAgentSkillId, type SubAgentSkillOption } from './subAgentOptions'

export function SubAgentSkillPicker({
  onAdoptSkill,
  onRemoveSkill,
  selectedSkills,
}: {
  onAdoptSkill: (skillId: SubAgentSkillId) => void
  onRemoveSkill: (skillId: SubAgentSkillId) => void
  selectedSkills: SubAgentSkillOption[]
}) {
  const selectedSkillIds = selectedSkills.map((skill) => skill.id)

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {SUB_AGENT_SKILLS.map((skill) => {
        const inputId = `sub-agent-skill-${skill.id}`
        const checked = selectedSkillIds.includes(skill.id)
        return (
          <label
            key={skill.id}
            htmlFor={inputId}
            className="border-border hover:bg-accent/40 flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors"
          >
            <Checkbox
              id={inputId}
              checked={checked}
              onCheckedChange={(next) => {
                if (next === true) {
                  onAdoptSkill(skill.id)
                } else {
                  onRemoveSkill(skill.id)
                }
              }}
              className="mt-0.5"
            />
            <span className="min-w-0">
              <span className="block text-sm font-medium">{skill.label}</span>
              <span className="text-muted-foreground mt-0.5 block text-xs leading-5">
                {skill.description}
              </span>
            </span>
          </label>
        )
      })}
    </div>
  )
}
