import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

export function useECharts(ref: React.RefObject<HTMLDivElement>) {
  const instance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    instance.current = echarts.init(ref.current, 'dark');
    const onResize = () => instance.current?.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      instance.current?.dispose();
      instance.current = null;
    };
  }, []);

  return instance;
}
