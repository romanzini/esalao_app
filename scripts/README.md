# Scripts Operacionais

## 1. Criar/Atualizar Labels

Cria ou atualiza labels de épicos e fases de forma idempotente.

```powershell
pwsh ./scripts/create_github_labels.ps1 -Repo "org/esalao_app" -DryRun   # visualizar
pwsh ./scripts/create_github_labels.ps1 -Repo "org/esalao_app"            # aplicar
```

## 2. Importar Issues

Executa leitura de todos arquivos `issues/GH-*.md`, extrai metadados (ID, Epic, Phase) e gera labels:
`auto-import`, labels base do arquivo, `epic:<slug>`, `phase:<n>`.

Dry run (não cria nada):
```powershell
pwsh ./scripts/create_github_issues.ps1 -Repo "org/esalao_app" -DryRun
```

Criar somente subset (regex IncludeFilter):
```powershell
pwsh ./scripts/create_github_issues.ps1 -Repo "org/esalao_app" -IncludeFilter "GH-00[1-5]" -DryRun
```

Criar efetivamente (todas):
```powershell
pwsh ./scripts/create_github_issues.ps1 -Repo "org/esalao_app" -SkipExisting
```

## 3. Ordem Recomendada

1. Criar/atualizar labels (DryRun -> aplicar).
2. Rodar issues script em DryRun e inspecionar saída.
3. Executar criação efetiva com `-SkipExisting`.
4. Criar saved searches no GitHub:
   - `label:phase:1 is:open`
   - `label:epic:scheduling-core is:open`
5. (Opcional) Vincular a um GitHub Project (Automation por label).

## 4. Segurança

- Scripts não persistem secrets; dependem da autenticação prévia do `gh` CLI.
- Verifique `gh auth status` antes.

## 5. Troubleshooting

| Problema | Causa Possível | Ação |
|----------|----------------|------|
| "gh CLI não encontrado" | GitHub CLI não instalado | Instalar: [GitHub CLI](https://cli.github.com/) |
| Labels duplicadas | Execução sem cores/descrição previas | Rodar script de labels para padronizar |
| Issues sem labels epic/phase | Metadados ausentes no arquivo | Verificar bloco HTML `<!-- ... -->` |
| Timeout criação issues | Rate limit org grande | Reexecutar após alguns minutos |

## 6. Extensões Futuras

- Adicionar opção `-LabelPrefix` para ambientes.
- Exportar relatório CSV de issues criadas.
- Integração com Projects API para auto-colocar em coluna inicial.
