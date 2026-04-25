import { StructuredItem } from '../../types/chat';
import { OptionCards } from './OptionCards';
import { QualityPanel } from './QualityPanel';
import { FileUploadZone } from './FileUploadZone';

interface Props {
  items: StructuredItem[];
  onOptionSelect?: (value: string) => void;
  onFileUpload?: (files: FileList) => void;
}

export function StructuredMessage({ items, onOptionSelect, onFileUpload }: Props) {
  return (
    <div className="space-y-3">
      {items.map((item, i) => {
        switch (item.type) {
          case 'text':
            return <p key={i} className="text-sm whitespace-pre-wrap">{item.content}</p>;
          case 'options':
            return (
              <div key={i}>
                <p className="text-sm mb-2">{item.content}</p>
                <OptionCards options={item.options || []} onSelect={onOptionSelect} />
              </div>
            );
          case 'panel':
            if (item.panel_type === 'quality_report') {
              const qdata = item.data as { score: number; issues: any[] } | undefined;
              return <QualityPanel key={i} data={qdata || { score: 0, issues: [] }} />;
            }
            return <p key={i} className="text-sm">{item.content}</p>;
          case 'file_upload':
            return (
              <div key={i}>
                <p className="text-sm mb-2">{item.content}</p>
                <FileUploadZone
                  accept={item.accept || '.xlsx,.xls,.csv'}
                  multiple={item.multiple ?? true}
                  onUpload={onFileUpload}
                />
              </div>
            );
          default:
            return <p key={i} className="text-sm">{item.content}</p>;
        }
      })}
    </div>
  );
}
