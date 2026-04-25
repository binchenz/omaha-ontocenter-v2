import { useCallback, useRef, useState } from 'react';

interface Props {
  accept: string;
  multiple: boolean;
  onUpload?: (files: FileList) => void;
}

export function FileUploadZone({ accept, multiple, onUpload }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      onUpload?.(e.dataTransfer.files);
    }
  }, [onUpload]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUpload?.(e.target.files);
    }
  }, [onUpload]);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
        dragOver ? 'border-blue-400 bg-blue-900/20' : 'border-gray-600 hover:border-gray-500'
      }`}
    >
      <p className="text-sm text-gray-400">拖拽文件到这里，或点击选择文件</p>
      <p className="text-xs text-gray-500 mt-1">支持 Excel (.xlsx, .xls) 和 CSV 文件</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleChange}
        className="hidden"
      />
    </div>
  );
}
