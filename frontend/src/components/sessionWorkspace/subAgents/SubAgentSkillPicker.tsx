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
    <div className="border-border border-t px-4 py-4">
      <div className="space-y-3">
        <div>
          <h2 className="text-sm font-medium">Session skills</h2>
          <p className="text-muted-foreground mt-1 text-xs">
            Optional skills available to this session agent. Built-in runtime skills are added
            automatically.
          </p>
        </div>
        <div className="space-y-3">
          {SUB_AGENT_SKILLS.map((skill) => {
            const inputId = `sub-agent-skill-${skill.id}`
            const checked = selectedSkillIds.includes(skill.id)
            return (
              <div key={skill.id} className="flex items-start gap-3">
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
                />
                <label htmlFor={inputId} className="grid gap-1 leading-none">
                  <span className="text-sm font-medium">{skill.label}</span>
                  <span className="text-muted-foreground text-xs">{skill.description}</span>
                </label>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
