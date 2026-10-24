# Backup

Programa para Windows que copia os arquivos de uma **pasta de origem** para uma **pasta de destino**, incluindo subpastas, sem sobrescrever o que já está mais atualizado.

## Como funciona

Para cada arquivo da origem:

| Situação no destino | O que acontece |
|---|---|
| Arquivo não existe | **copia** |
| Arquivo com conteúdo idêntico | **ignora** |
| Os dois têm versão (`.exe`, `.dll`...) e são diferentes | **substitui** só se a versão da origem for maior |
| Sem versão | **substitui** só se a data de modificação da origem for mais recente |

- A cópia preserva a data de modificação, então rodar de novo não copia nada que já esteja em dia.
- Diferença de até 2 s na data é tratada como igual (pendrives e HDs FAT/exFAT gravam a data com essa resolução).
- O destino não pode estar dentro da origem (nem o contrário).

## Uso

1. Abra `Backup.exe`
2. Escolha a **Origem** e o **Destino**
3. (Opcional) marque **Simular** para ver o que seria feito sem copiar nada
4. Clique em **Iniciar backup**

O log mostra cada arquivo copiado/substituído e o motivo; no final aparece o resumo.

## Gerar o executável

Requer Python 3 no Windows:

```bat
build.bat
```

Cria o ambiente virtual, roda os testes e gera `Backup.exe` com PyInstaller.

## Rodar sem compilar

```bat
python app.py
```

## Testes

```bat
python -m unittest discover -s tests -v
```

## Estrutura

```
backup.py          regra de decisão e cópia (sem interface)
app.py             interface Tkinter
tests/             testes unitários
build.bat          gera o Backup.exe
```
