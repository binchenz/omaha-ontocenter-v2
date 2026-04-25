interface Props {
  options: { label: string; value: string }[];
  onSelect?: (value: string) => void;
}

export function OptionCards({ options, onSelect }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onSelect?.(opt.value)}
          className="px-4 py-2 rounded-lg border border-gray-600 bg-gray-800 hover:bg-gray-700 text-sm text-gray-200 transition-colors"
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
