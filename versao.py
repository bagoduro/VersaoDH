#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import re
import csv
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = 1.5
MAX_WORKERS = 250          # Reduzido (mais estável e geralmente mais rápido no geral)
MAX_RETRIES = 1

def extract(pattern, text):
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else None


def create_session():
    """Cria uma session otimizada com pooling e retry leve"""
    session = requests.Session()
    retry = Retry(total=MAX_RETRIES, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=MAX_WORKERS * 2,
        pool_maxsize=MAX_WORKERS * 3,   # Pool maior que o número de workers
        pool_block=False
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return session


def collect(ip_or_host, default_port=None):
    # Se o host já contém ":" (ex: 192.168.0.10:80), usa ele diretamente.
    # Caso contrário, aplica a porta padrão se ela tiver sido informada.
    if ":" in ip_or_host:
        target_host = ip_or_host
    elif default_port:
        target_host = f"{ip_or_host}:{default_port}"
    else:
        target_host = ip_or_host

    target = target_host if "://" in target_host else f"http://{target_host}"
    target = target.rstrip('/')

    result = {
        "ip": target_host,
        "model": "", "web_version": "", "plugin_version": "",
        "http_port": "", "rtsp_port": "", "tcp_port": "",
        "stream_cap": "", "audio_type": "",
    }

    session = create_session()

    urls = {
        "cap": f"{target}/cap.js",
        "web": f"{target}/webVersion.js",
        "plugin": f"{target}/pluginVersion.js"
    }

    content = {}

    try:
        # === ALTERAÇÃO PRINCIPAL: Requisições sequenciais por alvo ===
        for key, url in urls.items():
            try:
                r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
                if r.status_code == 200:
                    content[key] = r.text
            except Exception:
                content[key] = ""

        if not any(content.values()):
            return None

        # Parsing (mantido igual)
        if content.get("cap"):
            cap = content["cap"]
            result["model"] = extract(r"devType\s*=\s*['\"]([^'\"]+)['\"]", cap) or ""
            result["rtsp_port"] = extract(r"rtspport\s*=\s*(\d+)", cap) or ""
            result["tcp_port"] = extract(r"capTcpPort\s*=\s*(\d+)", cap) or ""
            result["http_port"] = extract(r"httpPort\s*=\s*(\d+)", cap) or ""
            result["stream_cap"] = extract(r"streamCap\s*=\s*(\d+)", cap) or ""
            result["audio_type"] = extract(r'audioType\s*=\s*"([^"]+)"', cap) or ""

        if content.get("web"):
            m = re.search(r'VERSION_GUI\s*=\s*["\']version=([0-9,\.]+)', content["web"], re.I)
            if m:
                result["web_version"] = m.group(1).replace(",", ".")

        if content.get("plugin"):
            result["plugin_version"] = extract(r"PLUGINS_VERSION\s*=\s*['\"]([^'\"]+)['\"]", content["plugin"]) or ""

        if result["model"] or result["web_version"] or result["plugin_version"]:
            return result

    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-o", "--output", default="resultado.csv")
    parser.add_argument("-t", "--threads", type=int, default=MAX_WORKERS)
    parser.add_argument("-p", "--port", type=str, default=None)
    args = parser.parse_args()

    try:
        with open(args.file) as f:
            ips = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[-] Erro ao ler arquivo: {e}")
        sys.exit(1)

    total_alvos = len(ips)
    porta_msg = f"porta {args.port}" if args.port else "portas do arquivo/padrão 80"
    print(f"[*] Modo Turbo Ativado: {total_alvos} alvos na {porta_msg} com {args.threads} threads...")
    print("[*] Pressione Ctrl+C para parar e salvar o progresso atual.\n")

    resultados = []
    processados = 0

    try:
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {executor.submit(collect, ip, args.port): ip for ip in ips}
            
            for future in as_completed(futures):
                processados += 1
                ip = futures[future]
                
                porcentagem = (processados / total_alvos) * 100
                sys.stdout.write(f"\r[*] Progresso: {processados}/{total_alvos} ({porcentagem:.2f}%)")
                sys.stdout.flush()

                try:
                    result = future.result()
                    if result:
                        sys.stdout.write("\r" + " " * 90 + "\r")  # Limpa linha
                        print(
                            f"[+] {result['ip']} | "
                            f"{result['model']} | "
                            f"WEB {result['web_version']} | "
                            f"PLUGIN {result['plugin_version']}"
                        )
                        resultados.append(result)
                except Exception:
                    pass

    except KeyboardInterrupt:
        print("\n\n[-] Interrupção detectada! Salvando dados obtidos até agora...")

    print("\n")
    if resultados:
        with open(args.output, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=[
                    "ip", "model", "web_version", "plugin_version",
                    "http_port", "rtsp_port", "tcp_port", "stream_cap", "audio_type"
                ]
            )
            writer.writeheader()
            for row in resultados:
                writer.writerow(row)
        print(f"[+] {len(resultados)} hosts identificados e salvos em: {args.output}")
    else:
        print("[-] Nenhum dispositivo compatível foi encontrado.")


if __name__ == "__main__":
    main()
