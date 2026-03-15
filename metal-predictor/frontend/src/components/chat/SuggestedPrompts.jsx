import React from 'react'

const METAL_LABELS = { copper: 'Copper', zinc: 'Zinc', aluminum: 'Aluminium' }

function getPrompts(metal) {
  if (metal) {
    const label = METAL_LABELS[metal] || metal.charAt(0).toUpperCase() + metal.slice(1)
    return [
      `What is the current ${label} price trend?`,
      `Should I sell 50 MT of ${label} at current prices?`,
      `How has ${label} performed over the last year?`,
      `What factors are affecting ${label} prices?`,
    ]
  }
  return [
    'Compare copper vs zinc performance this year',
    'Which metal has the best selling opportunity today?',
    'What is the LME price outlook for aluminium?',
    'Should I diversify across all three metals?',
  ]
}

export default function SuggestedPrompts({ metal, onSelect }) {
  const prompts = getPrompts(metal)

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-400 dark:text-gray-500 text-center">
        Ask anything about LME metals, or try a suggestion:
      </p>
      <div className="flex flex-wrap gap-2 justify-center">
        {prompts.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onSelect(prompt)}
            className="border border-gray-200 dark:border-metal-border rounded-full px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400 hover:border-gold hover:text-gold transition-all cursor-pointer"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  )
}
