"""Servidor local do mapa: serve os arquivos e salva o progresso em disco.

- O que você marca como encontrado vai para progresso.json.
- Filtros, posição do mapa e grupos abertos vão para configuracao.json.
- Os dois ficam fora do git: rdr2map_pinos.json nunca é alterado.
- dados.js é gerado ao iniciar e alguns segundos depois de cada mudança, para o
  modo sem servidor (abrir o index.html com dois cliques) também ver o progresso.

Uso:
    python servidor.py           # abre http://localhost:8765 no navegador
    python servidor.py --porta 9000 --sem-navegador
"""

import argparse
import json
import os
import socket
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import preparar

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ_CONFIG = os.path.join(PASTA, "configuracao.json")
LIMITE_CORPO = 1_000_000

trava = threading.Lock()
ids_validos = {p["id"] for p in preparar.ler_pinos()}
encontrados = set(preparar.ler_encontrados())
try:
    with open(ARQ_CONFIG, encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}

timer_dados = None


def gravar_json(arquivo, dados):
    # Grava num temporário e troca, para não corromper o JSON se o processo
    # for fechado no meio.
    temp = arquivo + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    os.replace(temp, arquivo)


def agendar_dados_js():
    global timer_dados
    if timer_dados:
        timer_dados.cancel()
    timer_dados = threading.Timer(3, preparar.gerar_dados)
    timer_dados.daemon = True
    timer_dados.start()


def estado():
    return {
        "encontrados": sorted(encontrados),
        "config": config,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PASTA, **kwargs)

    def end_headers(self):
        # Sem cache: dados.js e o próprio index.html mudam
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, formato, *args):
        if self.path.startswith("/api/"):
            super().log_message(formato, *args)

    def responder(self, codigo, corpo):
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path == "/api/estado":
            with trava:
                return self.responder(200, estado())
        super().do_GET()

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho > LIMITE_CORPO:
            return self.responder(413, {"erro": "corpo grande demais"})
        try:
            corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        except ValueError:
            return self.responder(400, {"erro": "JSON inválido"})

        if self.path == "/api/encontrado":
            # {"ids": [1, 2], "encontrado": true}
            ids, valor = corpo.get("ids"), corpo.get("encontrado")
            if not isinstance(ids, list) or not isinstance(valor, bool):
                return self.responder(400, {"erro": "esperado {ids: [...], encontrado: bool}"})
            with trava:
                validos = {i for i in ids if i in ids_validos}
                if valor:
                    encontrados.update(validos)
                else:
                    encontrados.difference_update(validos)
                gravar_json(preparar.ARQ_PROGRESSO, {"encontrados": sorted(encontrados)})
                agendar_dados_js()
            return self.responder(200, {"ok": True})

        if self.path == "/api/config":
            # {"chave": "categorias", "valor": [...]}
            chave = corpo.get("chave")
            if not isinstance(chave, str) or not chave or len(chave) > 100:
                return self.responder(400, {"erro": "chave inválida"})
            with trava:
                config[chave] = corpo.get("valor")
                gravar_json(ARQ_CONFIG, config)
            return self.responder(200, {"ok": True})

        self.responder(404, {"erro": "rota desconhecida"})


class ServidorExclusivo(ThreadingHTTPServer):
    # No Windows, o padrão deixa dois servidores abrirem na mesma porta, e cada um
    # guardaria o progresso por cima do outro
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def ip_da_rede():
    # Conectar um socket UDP não envia nada; só faz o sistema escolher a placa de rede
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "IP-DESTE-PC"
    finally:
        s.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--porta", type=int, default=8765)
    parser.add_argument("--sem-navegador", action="store_true", help="não abre o navegador")
    parser.add_argument("--so-este-pc", action="store_true", help="não aceita conexões de outros aparelhos")
    args = parser.parse_args()

    # 0.0.0.0 = aceita celular e outros aparelhos da mesma rede Wi-Fi
    endereco = "127.0.0.1" if args.so_este_pc else "0.0.0.0"
    try:
        servidor = ServidorExclusivo((endereco, args.porta), Handler)
    except OSError:
        raise SystemExit(f"A porta {args.porta} já está em uso: o mapa já deve estar aberto em outra janela.")
    url = f"http://localhost:{args.porta}/"
    print(f"Mapa rodando em {url}")
    if not args.so_este_pc:
        print(f"No celular (mesma rede Wi-Fi): http://{ip_da_rede()}:{args.porta}/")
    preparar.gerar_dados()
    print("Feche esta janela (ou Ctrl+C) para parar.")
    if not args.sem_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if timer_dados and timer_dados.is_alive():
            timer_dados.cancel()
            preparar.gerar_dados()


if __name__ == "__main__":
    main()
