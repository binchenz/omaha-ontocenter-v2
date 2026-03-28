import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Trash2, FolderOpen, Calendar, Database, GitBranch } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { assetService, Asset, AssetLineage } from '@/services/asset';
import LineageGraph from '@/components/LineageGraph';

const AssetList: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const projectId = id ? parseInt(id) : undefined;

  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [lineageModalOpen, setLineageModalOpen] = useState(false);
  const [lineageLoading, setLineageLoading] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [lineageData, setLineageData] = useState<AssetLineage>({ upstream: [], downstream: [] });

  useEffect(() => { if (projectId) loadAssets(); }, [projectId]);

  const loadAssets = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      setAssets(await assetService.listAssets(projectId));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, asset: Asset) => {
    e.stopPropagation();
    if (!projectId || !window.confirm(`Delete "${asset.name}"?`)) return;
    await assetService.deleteAsset(projectId, asset.id);
    loadAssets();
  };

  const handleViewLineage = async (e: React.MouseEvent, asset: Asset) => {
    e.stopPropagation();
    if (!projectId) return;
    setSelectedAsset(asset);
    setLineageModalOpen(true);
    setLineageLoading(true);
    try {
      setLineageData(await assetService.getLineage(projectId, asset.id));
    } catch {
      setLineageData({ upstream: [], downstream: [] });
    } finally {
      setLineageLoading(false);
    }
  };

  const formatDate = (d: string) => new Date(d).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  if (loading) {
    return <p className="text-slate-400 text-sm text-center py-12">Loading...</p>;
  }

  return (
    <div>
      <Card className="bg-surface border-white/10">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <FolderOpen size={18} /> Saved Assets
          </CardTitle>
        </CardHeader>
        <CardContent>
          {assets.length === 0 ? (
            <p className="text-slate-400 text-sm text-center py-12">No saved assets yet</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {assets.map(asset => (
                <div key={asset.id}
                  className="border border-white/10 rounded-lg p-4 bg-background hover:bg-white/5 cursor-pointer space-y-3">
                  <div>
                    <p className="text-white font-medium">{asset.name}</p>
                    <Badge variant="secondary" className="mt-1 text-xs">{asset.query_config.object_type}</Badge>
                  </div>
                  {asset.description && (
                    <p className="text-slate-400 text-xs line-clamp-2">{asset.description}</p>
                  )}
                  <div className="space-y-1 text-xs text-slate-500">
                    {asset.row_count !== undefined && (
                      <div className="flex items-center gap-1"><Database size={11} /> {asset.row_count} rows</div>
                    )}
                    <div className="flex items-center gap-1"><Calendar size={11} /> {formatDate(asset.created_at)}</div>
                  </div>
                  <div className="flex gap-2 pt-1">
                    <Button variant="ghost" size="sm" onClick={e => handleViewLineage(e, asset)}
                      className="text-slate-400 hover:text-white text-xs h-7">
                      <GitBranch size={12} className="mr-1" /> 血缘
                    </Button>
                    <Button variant="ghost" size="sm" onClick={e => handleDelete(e, asset)}
                      className="text-red-400 hover:text-red-300 text-xs h-7">
                      <Trash2 size={12} className="mr-1" /> Delete
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={lineageModalOpen} onOpenChange={setLineageModalOpen}>
        <DialogContent className="bg-surface border-white/10 text-white max-w-3xl">
          <DialogHeader>
            <DialogTitle>数据血缘 - {selectedAsset?.name}</DialogTitle>
          </DialogHeader>
          {lineageLoading ? (
            <p className="text-slate-400 text-sm text-center py-12">Loading...</p>
          ) : (
            <LineageGraph assetName={selectedAsset?.name || ''} lineage={lineageData} />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AssetList;
