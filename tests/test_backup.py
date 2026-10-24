import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import backup  # noqa: E402


def escrever(caminho, conteudo, mtime=None):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    if mtime is not None:
        os.utime(caminho, (mtime, mtime))


def ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


class TestBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.origem = os.path.join(self.tmp.name, "origem")
        self.destino = os.path.join(self.tmp.name, "destino")
        os.makedirs(self.origem)
        self.agora = time.time()

    def tearDown(self):
        self.tmp.cleanup()

    def o(self, *p):
        return os.path.join(self.origem, *p)

    def d(self, *p):
        return os.path.join(self.destino, *p)

    def test_copia_arquivo_novo_e_subpastas(self):
        escrever(self.o("a.txt"), "A")
        escrever(self.o("sub", "b.txt"), "B")
        res = backup.executar(self.origem, self.destino)
        self.assertEqual(res.copiados, 2)
        self.assertEqual(ler(self.d("sub", "b.txt")), "B")

    def test_substitui_quando_origem_mais_recente(self):
        escrever(self.o("a.txt"), "novo", self.agora)
        escrever(self.d("a.txt"), "velho", self.agora - 3600)
        res = backup.executar(self.origem, self.destino)
        self.assertEqual(res.substituidos, 1)
        self.assertEqual(ler(self.d("a.txt")), "novo")

    def test_nao_substitui_quando_destino_mais_recente(self):
        escrever(self.o("a.txt"), "velho", self.agora - 3600)
        escrever(self.d("a.txt"), "novo", self.agora)
        res = backup.executar(self.origem, self.destino)
        self.assertEqual(res.ignorados, 1)
        self.assertEqual(ler(self.d("a.txt")), "novo")

    def test_ignora_identico_mesmo_com_data_diferente(self):
        escrever(self.o("a.txt"), "igual", self.agora)
        escrever(self.d("a.txt"), "igual", self.agora - 3600)
        acao, _ = backup.decidir(self.o("a.txt"), self.d("a.txt"))
        self.assertEqual(acao, backup.IGNORAR)

    def test_diferenca_dentro_da_tolerancia_nao_substitui(self):
        escrever(self.o("a.txt"), "x", self.agora + 1)
        escrever(self.d("a.txt"), "y", self.agora)
        acao, _ = backup.decidir(self.o("a.txt"), self.d("a.txt"))
        self.assertEqual(acao, backup.IGNORAR)

    def test_versao_maior_substitui_mesmo_com_data_antiga(self):
        escrever(self.o("p.exe"), "v2", self.agora - 3600)
        escrever(self.d("p.exe"), "v1", self.agora)
        versoes = {self.o("p.exe"): (2, 0, 0, 0), self.d("p.exe"): (1, 0, 0, 0)}
        acao, _ = backup.decidir(self.o("p.exe"), self.d("p.exe"), versoes.get)
        self.assertEqual(acao, backup.SUBSTITUIR)

    def test_versao_menor_nao_substitui_mesmo_com_data_nova(self):
        escrever(self.o("p.exe"), "v1", self.agora)
        escrever(self.d("p.exe"), "v2", self.agora - 3600)
        versoes = {self.o("p.exe"): (1, 0, 0, 0), self.d("p.exe"): (2, 0, 0, 0)}
        acao, _ = backup.decidir(self.o("p.exe"), self.d("p.exe"), versoes.get)
        self.assertEqual(acao, backup.IGNORAR)

    def test_segunda_execucao_nao_copia_nada(self):
        escrever(self.o("a.txt"), "A")
        backup.executar(self.origem, self.destino)
        res = backup.executar(self.origem, self.destino)
        self.assertEqual((res.copiados, res.substituidos, res.ignorados), (0, 0, 1))

    def test_simular_nao_grava(self):
        escrever(self.o("a.txt"), "A")
        res = backup.executar(self.origem, self.destino, simular=True)
        self.assertEqual(res.copiados, 1)
        self.assertFalse(os.path.exists(self.d("a.txt")))

    def test_destino_dentro_da_origem_e_recusado(self):
        with self.assertRaises(ValueError):
            backup.executar(self.origem, self.o("copia"))

    def test_origem_inexistente(self):
        with self.assertRaises(ValueError):
            backup.executar(self.o("nao_existe"), self.destino)

    @unittest.skipUnless(sys.platform == "win32", "so no Windows")
    def test_le_versao_de_exe_do_windows(self):
        notepad = os.path.join(os.environ["WINDIR"], "System32", "notepad.exe")
        self.assertIsNotNone(backup.versao_arquivo(notepad))
        self.assertIsNone(backup.versao_arquivo(__file__))


if __name__ == "__main__":
    unittest.main()
