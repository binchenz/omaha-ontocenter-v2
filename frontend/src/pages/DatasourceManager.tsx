import React, { useState, useEffect, useRef } from 'react';
import { Upload, CheckCircle, XCircle, Loader2, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { datasourceService, DatasourceInfo, ColumnInfo } from '@/services/datasource';

interface Props { projectId: number; }

const DatasourceManager: React.FC<Props> = ({ projectId }) => {
  const navigate = useNavigate();
  const [datasources, setDatasources] = useState<DatasourceInfo[]>([]);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, boolean>>({});
  const [uploading, setUploading] = useState(false);
  const [tableName, setTableName] = useState('');
  const [uploadResult, setUploadResult] = useState<{ columns: ColumnInfo[]; tableName: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { loadDatasources(); }, [projectId]);

  const loadDatasources = async () => {
    const ds = await datasourceService.list(projectId);
    setDatasources(ds);
  };

  const handleTest = async (ds: DatasourceInfo) => {
    setTesting(ds.id);
    const result = await datasourceService.testConnection(projectId, ds.type, {});
    setTestResults(prev => ({ ...prev, [ds.id]: result.connected }));
    setTesting(null);
  };

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !tableName) return;
    setUploading(true);
    try {
      const result = await datasourceService.upload(projectId, file, tableName);
      if (result.success) {
        setUploadResult({ columns: result.columns, tableName });
        loadDatasources(); // refresh datasource list (csv_imported now appears)
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="bg-surface border-white/10">
        <CardHeader><CardTitle className="text-white text-base">已配置的数据源</CardTitle></CardHeader>
        <CardContent>
          {datasources.length === 0 ? (
            <p className="text-slate-400 text-sm">暂无数据源，请在配置编辑中添加</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-white/10">
                  <TableHead className="text-slate-400">名称</TableHead>
                  <TableHead className="text-slate-400">类型</TableHead>
                  <TableHead className="text-slate-400">状态</TableHead>
                  <TableHead className="text-slate-400"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {datasources.map(ds => (
                  <TableRow key={ds.id} className="border-white/10">
                    <TableCell className="text-white">{ds.name}</TableCell>
                    <TableCell className="text-slate-400 font-mono text-xs">{ds.type}</TableCell>
                    <TableCell>
                      {testResults[ds.id] !== undefined ? (
                        testResults[ds.id]
                          ? <CheckCircle size={14} className="text-green-400" />
                          : <XCircle size={14} className="text-red-400" />
                      ) : <span className="text-slate-500 text-xs">未测试</span>}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" onClick={() => handleTest(ds)}
                        disabled={testing === ds.id} className="text-xs text-slate-400">
                        {testing === ds.id ? <Loader2 size={12} className="animate-spin" /> : '测试连接'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card className="bg-surface border-white/10">
        <CardHeader><CardTitle className="text-white text-base">上传 CSV / Excel</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label className="text-slate-300">表名 *</Label>
            <Input value={tableName} onChange={e => setTableName(e.target.value)}
              placeholder="如: sales_data" className="bg-background border-white/10 text-white font-mono" />
          </div>
          <div className="space-y-1">
            <Label className="text-slate-300">文件</Label>
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls"
              className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:bg-primary/20 file:text-primary hover:file:bg-primary/30" />
          </div>
          <Button onClick={handleUpload} disabled={uploading || !tableName}
            className="bg-primary hover:bg-primary/90">
            <Upload size={14} className="mr-2" /> {uploading ? '上传中...' : '上传并导入'}
          </Button>

          {uploadResult && (
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-green-400 text-sm">导入成功，推断的 Schema：</p>
                <Button
                  size="sm"
                  onClick={() => navigate('/explorer', { state: { preselect: uploadResult.tableName } })}
                  className="bg-primary hover:bg-primary/90 text-xs"
                >
                  <Search size={12} className="mr-1" /> 在 Explorer 中查询
                </Button>
              </div>
              <Table>
                <TableHeader>
                  <TableRow className="border-white/10">
                    <TableHead className="text-slate-400">列名</TableHead>
                    <TableHead className="text-slate-400">类型</TableHead>
                    <TableHead className="text-slate-400">可空</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {uploadResult.columns.map(col => (
                    <TableRow key={col.name} className="border-white/10">
                      <TableCell className="text-white font-mono text-xs">{col.name}</TableCell>
                      <TableCell className="text-slate-400 text-xs">{col.type}</TableCell>
                      <TableCell className="text-slate-400 text-xs">{col.nullable ? '是' : '否'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DatasourceManager;
