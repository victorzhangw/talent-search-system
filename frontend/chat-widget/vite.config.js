import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { viteStaticCopy } from 'vite-plugin-static-copy'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    viteStaticCopy({
      targets: [
        {
          src: 'src/assets/images/*',
          dest: 'assets/images'
        }
      ]
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5300
  },
  build: {
    lib: {
      // Could also be a dictionary or array of multiple entry points
      entry: resolve(__dirname, 'src/main.js'),
      name: 'ChatWidget',
      // the proper extensions will be added
      fileName: 'loader',
      formats: ['iife'] // Immediately Invoked Function Expression for direct script injection
    },
    rollupOptions: {
      // make sure to externalize deps that shouldn't be bundled
      // into your library
      external: [],
      output: {
        // Provide global variables to use in the UMD build
        // for externalized deps
        globals: {
          vue: 'Vue'
        },
        // Force CSS to be injected or extracted. 
        // For a single file widget, inline CSS or a single css file is good.
        // Vite by default emits style.css. 
        assetFileNames: (assetInfo) => {
          if (assetInfo.name === 'style.css') return 'loader.css';
          return assetInfo.name;
        },
      }
    },
    // Ensure CSS is included or handled
    cssCodeSplit: false
  },
  define: {
    'process.env': {}
  }
})
