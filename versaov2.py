#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import re
import csv
import argparse
import sys
import logging
import socket
from aiohttp import ClientSession, TCPConnector, ClientTimeout
from aiohttp_retry import RetryClient, ExponentialRetry

# ==================== SILENCIAR LOGS ====================
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp_retry").setLevel(logging.ERROR)

def silence_gaierror(loop, context):
    exception = context.get('exception')
    if exception and (isinstance(exception, (socket.gaierror, OSError))):
        if 'Too many open files' in str(exception) or 'DNS' in str(exception):
            return
    loop.default_exception_handler(context)

# ==================== CONFIGURAÇÕES ====================
TIMEOUT = 2.0
MAX_CONCURRENT = 120         # Aumentado novamente (teste entre 100-150)
# =======================================================

def extract(pattern, text):
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else None

async def collect(semaphore, session, ip_or_host, default_port=None):
    async with semaphore:
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
            "model": "",
            "http_port": "", "rtsp_port": "", "tcp_port": "",
            "stream_cap": "", "audio_type": "",
        }

        url = f"{target}/cap.js"

        try:
            async with session.get(url, allow_redirects=True) as r:
                if r.status != 200:
                    return None

                cap = await r.text()
                result["model"] = extract(r"devType\s*=\s*['\"]([^'\"]+)['\"]", cap) or ""
                result["rtsp_port"] = extract(r"rtspport\s*=\s*(\d+)", cap) or ""
                result["tcp_port"] = extract(r"capTcpPort\s*=\s*(\d+)", cap) or ""
                result["http_port"] = extract(r"httpPort\s*=\s*(\d+)", cap) or ""
                result["stream_cap"] = extract(r"streamCap\s*=\s*(\d+)", cap) or ""
                result["audio_type"] = extract(r'audioType\s*=\s*"([^"]+)"', cap) or ""

                if result["model"] or result["tcp_port"] or result["rtsp_port"]:
                    return result
        except asyncio.TimeoutError:
            pass
        except OSError as e:
            if e.errno == 24:  # Too many open files
                await asyncio.sleep(0.1)
            pass
        except Exception:
            pass
        return None


async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(silence_gaierror)

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-o", "--output", default="resultado.csv")
    parser.add_argument("-t", "--concurrent", type=int, default=MAX_CONCURRENT)
    parser.add_argument("-p", "--port", type=str, default=None)
    args = parser.parse_args()

    try:
        with open(args.file, encoding="utf-8") as f:
            ips = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except Exception as e:
        print(f"[-] Erro ao ler arquivo: {e}")
        sys.exit(1)

    total_alvos = len(ips)
    print(f"[*] Async Turbo v3.3 → {total_alvos:,} alvos | {args.concurrent} conexões simultâneas")
    print("[*] Modo velocidade otimizado\n")

    # Connector mais rápido
    connector = TCPConnector(
        limit=args.concurrent * 2,
        limit_per_host=12,
        ttl_dns_cache=900,
        keepalive_timeout=30,
        use_dns_cache=True,
        happy_eyeballs_delay=0.25,
    )

    timeout = ClientTimeout(total=TIMEOUT, sock_connect=1.6, sock_read=2.2)
    retry_options = ExponentialRetry(attempts=1, start_timeout=0.25, max_timeout=1.0)

    resultados = []
    processados = 0
    semaphore = asyncio.Semaphore(args.concurrent)

    try:
        async with RetryClient(
            retry_options=retry_options,
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        ) as session:
            
            tasks = [collect(semaphore, session, ip, args.port) for ip in ips]
            
            for future in asyncio.as_completed(tasks):
                result = await future
                processados += 1
                
                if result:
                    resultados.append(result)
                    print(f"[+] {result['ip']} | Modelo: {result['model']} | "
                          f"HTTP: {result['http_port']} | RTSP: {result['rtsp_port']} | TCP: {result['tcp_port']}")

                # Progresso correto e limpo
                porcentagem = (processados / total_alvos) * 100
                sys.stdout.write(f"\r[*] Progresso: {processados:,}/{total_alvos:,} ({porcentagem:.1f}%) | Encontrados: {len(resultados)}")
                sys.stdout.flush()

    except asyncio.CancelledError:
        print("\n\n[-] Interrupção detectada (Ctrl+C)")
    except Exception as e:
        print(f"\n[-] Erro: {e}")
    finally:
        # Salvamento garantido
        if resultados:
            with open(args.output, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=[
                    "ip", "model", "http_port", "rtsp_port", "tcp_port", "stream_cap", "audio_type"
                ])
                writer.writeheader()
                writer.writerows(resultados)
            print(f"\n\n[+] {len(resultados)} dispositivos salvos em → {args.output}")
        else:
            print("\n[-] Nenhum dispositivo encontrado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[-] Script finalizado pelo usuário.")
