# LucraFood: frontend

React + TypeScript (Vite). Telas: foto do cardápio → revisão → painel com semáforo.

```bash
npm install
npm run dev      # http://localhost:5173 (o /api é repassado ao Django em localhost:8000)
npm test         # testes de formatação (vitest)
npm run build    # checa os tipos e gera dist/
```

O backend precisa estar rodando (`cd backend && python manage.py runserver`).
No Windows com o Controle Inteligente de Aplicativos ligado, o binário nativo do Rollup é bloqueado;
por isso o `package.json` usa `overrides` para o `@rollup/wasm-node` (mesma versão, sem binário nativo).
