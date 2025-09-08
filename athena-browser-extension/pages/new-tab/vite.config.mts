import { resolve } from 'node:path';
import { withPageConfig } from '@extension/vite-config';
import svgr from 'vite-plugin-svgr';
import type { PluginOption } from 'vite';

const rootDir = resolve(import.meta.dirname);
const srcDir = resolve(rootDir, 'src');

export default withPageConfig({
  plugins: [
    (() => {
      const svgrCfg: any = {
        include: '**/*.svg',
        exportAsDefault: true,
        svgrOptions: {
          exportType: 'default',
          svgo: true,
          svgoConfig: {
            plugins: [
              { name: 'preset-default' },
              { name: 'removeDimensions' },
              { name: 'prefixIds' },
              { name: 'removeScriptElement' },
            ],
          },
        },
      };
      return svgr(svgrCfg) as unknown as PluginOption;
    })(),
  ],
  resolve: {
    alias: {
      '@src': srcDir,
      '@/app': srcDir,
    },
  },
  publicDir: resolve(rootDir, 'public'),
  build: {
    outDir: resolve(rootDir, '..', '..', 'dist', 'new-tab'),
    sourcemap: 'inline',
  },
});
