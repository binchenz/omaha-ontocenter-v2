import type { ReactNode } from 'react';
import { StructuredItem } from '../../types/chat';
import { OptionCards } from './OptionCards';
import { QualityPanel } from './QualityPanel';
import { OntologyConfirmPanel } from './OntologyConfirmPanel';
import { FileUploadZone } from './FileUploadZone';

interface Props {
  items: StructuredItem[];
  onOptionSelect?: (value: string) => void;
  onFileUpload?: (files: FileList) => void;
}

function LabeledBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-sm mb-2">{label}</p>
      {children}
    </div>
  );
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
              <LabeledBlock key={i} label={item.content}>
                <OptionCards options={item.options || []} onSelect={onOptionSelect} />
              </LabeledBlock>
            );
          case 'panel':
            if (item.panel_type === 'quality_report') {
              const qdata = item.data as { score: number; issues: any[] } | undefined;
              return <QualityPanel key={i} data={qdata || { score: 0, issues: [] }} />;
            }
            if (item.panel_type === 'ontology_preview') {
              return (
                <OntologyConfirmPanel
                  key={i}
                  data={item.data as any || { objects: [], relationships: [] }}
                  onConfirm={() => onOptionSelect?.('确认建模')}
                  onRetry={() => onOptionSelect?.('重新分析建模')}
                />
              );
            }
            return <p key={i} className="text-sm">{item.content}</p>;
          case 'file_upload':
            return (
              <LabeledBlock key={i} label={item.content}>
                <FileUploadZone
                  accept={item.accept || '.xlsx,.xls,.csv'}
                  multiple={item.multiple ?? true}
                  onUpload={onFileUpload}
                />
              </LabeledBlock>
            );
          default:
            return <p key={i} className="text-sm">{item.content}</p>;
        }
      })}
    </div>
  );
}
