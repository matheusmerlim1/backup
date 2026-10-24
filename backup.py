"""Nucleo do backup: decide, arquivo a arquivo, se copia, substitui ou ignora.

Regra para arquivo que ja existe no destino:
  1. conteudo identico                -> ignora
  2. os dois tem versao (exe, dll...) -> substitui so se a origem for de versao maior
  3. senao, compara a data de modificacao -> substitui so se a origem for mais recente
"""

import filecmp
import os
import shutil
import sys
from dataclasses import dataclass, field

# FAT/exFAT (pendrive, HD externo) guarda a data com resolucao de 2 segundos
TOLERANCIA_SEG = 2.0

COPIAR = "copiar"
SUBSTITUIR = "substituir"
IGNORAR = "ignorar"


def versao_arquivo(caminho):
    """Versao do arquivo (ex.: (1, 2, 0, 5)) lida do recurso de versao do Windows.

    Retorna None se nao for Windows ou se o arquivo nao tiver versao.
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    versao = ctypes.windll.version
    tamanho = versao.GetFileVersionInfoSizeW(caminho, None)
    if not tamanho:
        return None
    buffer = ctypes.create_string_buffer(tamanho)
    if not versao.GetFileVersionInfoW(caminho, 0, tamanho, buffer):
        return None

    ponteiro = ctypes.c_void_p()
    comprimento = wintypes.UINT()
    if not versao.VerQueryValueW(buffer, "\\", ctypes.byref(ponteiro), ctypes.byref(comprimento)):
        return None

    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [(nome, wintypes.DWORD) for nome in (
            "dwSignature", "dwStrucVersion", "dwFileVersionMS", "dwFileVersionLS",
            "dwProductVersionMS", "dwProductVersionLS", "dwFileFlagsMask", "dwFileFlags",
            "dwFileOS", "dwFileType", "dwFileSubtype", "dwFileDateMS", "dwFileDateLS")]

    info = ctypes.cast(ponteiro, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
    if info.dwSignature != 0xFEEF04BD:
        return None
    ms, ls = info.dwFileVersionMS, info.dwFileVersionLS
    return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)


def decidir(origem, destino, ler_versao=versao_arquivo):
    """Retorna (acao, motivo) para o par origem/destino."""
    if not os.path.exists(destino):
        return COPIAR, "novo"

    st_o, st_d = os.stat(origem), os.stat(destino)
    if st_o.st_size == st_d.st_size and filecmp.cmp(origem, destino, shallow=False):
        return IGNORAR, "identico"

    v_o, v_d = ler_versao(origem), ler_versao(destino)
    if v_o is not None and v_d is not None and v_o != v_d:
        texto = f"versao {'.'.join(map(str, v_o))} x {'.'.join(map(str, v_d))}"
        if v_o > v_d:
            return SUBSTITUIR, texto + " (origem mais nova)"
        return IGNORAR, texto + " (destino mais novo)"

    if st_o.st_mtime - st_d.st_mtime > TOLERANCIA_SEG:
        return SUBSTITUIR, "data de modificacao mais recente"
    return IGNORAR, "destino igual ou mais recente"


@dataclass
class Resultado:
    copiados: int = 0
    substituidos: int = 0
    ignorados: int = 0
    erros: list = field(default_factory=list)


def _dentro(pasta, outra):
    pasta, outra = os.path.normcase(os.path.abspath(pasta)), os.path.normcase(os.path.abspath(outra))
    return outra == pasta or outra.startswith(pasta.rstrip(os.sep) + os.sep)


def executar(origem, destino, simular=False, aviso=None, parar=None, ler_versao=versao_arquivo):
    """Copia a arvore `origem` para `destino` seguindo a regra de `decidir`.

    aviso(acao, caminho_relativo, motivo) e chamado a cada arquivo.
    parar() -> True interrompe o processo.
    """
    if not os.path.isdir(origem):
        raise ValueError(f"Pasta de origem nao existe: {origem}")
    if _dentro(origem, destino) or _dentro(destino, origem):
        raise ValueError("A pasta de destino nao pode estar dentro da origem (nem o contrario).")

    aviso = aviso or (lambda *a: None)
    res = Resultado()

    for raiz, pastas, arquivos in os.walk(origem):
        if parar and parar():
            break
        relativo_raiz = os.path.relpath(raiz, origem)
        pasta_destino = os.path.normpath(os.path.join(destino, relativo_raiz))

        for nome in arquivos:
            if parar and parar():
                break
            arq_o = os.path.join(raiz, nome)
            arq_d = os.path.join(pasta_destino, nome)
            relativo = os.path.normpath(os.path.join(relativo_raiz, nome))
            try:
                acao, motivo = decidir(arq_o, arq_d, ler_versao)
                if acao != IGNORAR and not simular:
                    os.makedirs(pasta_destino, exist_ok=True)
                    shutil.copy2(arq_o, arq_d)
                if acao == COPIAR:
                    res.copiados += 1
                elif acao == SUBSTITUIR:
                    res.substituidos += 1
                else:
                    res.ignorados += 1
                aviso(acao, relativo, motivo)
            except OSError as erro:
                res.erros.append((relativo, str(erro)))
                aviso("erro", relativo, str(erro))
    return res
