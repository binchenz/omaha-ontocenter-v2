import React from 'react';
import { Database } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ObjectListProps {
  objects: string[];
  selected: string | null;
  onSelect: (name: string) => void;
}

const ObjectList: React.FC<ObjectListProps> = ({ objects, selected, onSelect }) => {
  return (
    <div>
      {objects.map(name => (
        <div
          key={name}
          onClick={() => onSelect(name)}
          className={cn(
            'flex items-center gap-2 px-4 py-2 cursor-pointer text-sm border-l-2 transition-colors',
            selected === name
              ? 'bg-primary/10 text-primary border-primary font-medium'
              : 'text-slate-400 hover:text-white hover:bg-white/5 border-transparent'
          )}
        >
          <Database size={14} className="shrink-0" />
          {name}
        </div>
      ))}
    </div>
  );
};

export default ObjectList;
