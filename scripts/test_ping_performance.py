#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste de performance para a página PING
Testa se as otimizações resolveram o problema de travamento
Autor: Sistema de otimização automática
Data: 2025-10-31
"""

import requests
import time
import sys
from datetime import datetime

# Configuração
BASE_URL = "https://automacao.tce.go.gov.br/RFID"
# Para testes locais, use:
# BASE_URL = "http://localhost:5000/RFID"

TIMEOUT = 15  # segundos
NUM_TESTES = 5

def teste_endpoint(nome, url, timeout=TIMEOUT):
    """Testa um endpoint e retorna tempo de resposta"""
    print(f"\n{'='*60}")
    print(f"Testando: {nome}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    tempos = []
    erros = 0
    
    for i in range(NUM_TESTES):
        print(f"\nTeste {i+1}/{NUM_TESTES}...", end=" ", flush=True)
        inicio = time.time()
        
        try:
            response = requests.get(url, timeout=timeout, verify=False)
            tempo = time.time() - inicio
            tempos.append(tempo)
            
            if response.status_code == 200:
                print(f"✓ OK ({tempo:.2f}s)")
                
                # Verificar se é JSON
                try:
                    data = response.json()
                    if 'success' in data:
                        print(f"   Success: {data['success']}")
                    if 'total' in data:
                        print(f"   Total registros: {data['total']}")
                    if 'from_cache' in data:
                        print(f"   Cache: {data['from_cache']}")
                    if 'warning' in data:
                        print(f"   ⚠️  Warning: {data['warning']}")
                except:
                    print(f"   Resposta não é JSON (pode ser HTML)")
            else:
                print(f"✗ ERRO HTTP {response.status_code}")
                erros += 1
                
        except requests.Timeout:
            tempo = timeout
            print(f"✗ TIMEOUT após {tempo}s")
            erros += 1
            
        except requests.ConnectionError as e:
            print(f"✗ ERRO DE CONEXÃO: {e}")
            erros += 1
            return None
            
        except Exception as e:
            print(f"✗ ERRO: {e}")
            erros += 1
    
    # Estatísticas
    if tempos:
        print(f"\n{'─'*60}")
        print(f"📊 ESTATÍSTICAS:")
        print(f"   Tempo médio: {sum(tempos)/len(tempos):.2f}s")
        print(f"   Tempo mínimo: {min(tempos):.2f}s")
        print(f"   Tempo máximo: {max(tempos):.2f}s")
        print(f"   Taxa de sucesso: {((NUM_TESTES-erros)/NUM_TESTES)*100:.1f}%")
        
        # Avaliação
        tempo_medio = sum(tempos)/len(tempos)
        if tempo_medio < 1:
            print(f"   🟢 EXCELENTE - Muito rápido!")
        elif tempo_medio < 3:
            print(f"   🟡 BOM - Performance aceitável")
        elif tempo_medio < 5:
            print(f"   🟠 REGULAR - Pode melhorar")
        else:
            print(f"   🔴 LENTO - Ainda precisa otimização")
        
        return tempo_medio
    else:
        print(f"\n❌ Todos os testes falharam!")
        return None

def main():
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║      TESTE DE PERFORMANCE - PÁGINA PING OTIMIZADA        ║
║                                                           ║
║  Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}                            ║
║  Base URL: {BASE_URL:40s} ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    print("\n⚠️  Nota: Certificados SSL sendo ignorados para testes")
    print("         (use verify=True em produção)\n")
    
    # Desabilitar warning de SSL
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Testes
    resultados = {}
    
    # 1. Teste da API de listagem de PINGs (primeira página)
    resultados['ping_list'] = teste_endpoint(
        "API - Listar PINGs (página 1)",
        f"{BASE_URL}/api/ping?limite=50&offset=0"
    )
    
    time.sleep(2)  # Aguardar entre testes
    
    # 2. Teste da API de estatísticas
    resultados['ping_stats'] = teste_endpoint(
        "API - Estatísticas de PINGs",
        f"{BASE_URL}/api/ping/estatisticas"
    )
    
    time.sleep(2)
    
    # 3. Teste da API de listagem com filtro
    resultados['ping_filtered'] = teste_endpoint(
        "API - PINGs Filtrados",
        f"{BASE_URL}/api/ping?limite=50&offset=0&etiqueta=PING"
    )
    
    time.sleep(2)
    
    # 4. Teste da página HTML (se aplicável)
    resultados['ping_page'] = teste_endpoint(
        "Página HTML - PING",
        f"{BASE_URL}/ping"
    )
    
    # Relatório final
    print(f"\n\n{'═'*60}")
    print(f"📋 RELATÓRIO FINAL")
    print(f"{'═'*60}")
    
    total_sucesso = sum(1 for v in resultados.values() if v is not None)
    total_testes = len(resultados)
    
    print(f"\nTestes executados: {total_testes}")
    print(f"Testes bem-sucedidos: {total_sucesso}")
    print(f"Taxa de sucesso geral: {(total_sucesso/total_testes)*100:.1f}%")
    
    if total_sucesso > 0:
        tempos_validos = [v for v in resultados.values() if v is not None]
        tempo_medio_geral = sum(tempos_validos) / len(tempos_validos)
        print(f"\nTempo médio geral: {tempo_medio_geral:.2f}s")
        
        if tempo_medio_geral < 2:
            print("\n✅ OTIMIZAÇÃO BEM-SUCEDIDA!")
            print("   As mudanças melhoraram significativamente a performance.")
        elif tempo_medio_geral < 5:
            print("\n⚠️  OTIMIZAÇÃO PARCIAL")
            print("   Houve melhoria, mas ainda pode ser otimizado.")
        else:
            print("\n❌ AINDA REQUER ATENÇÃO")
            print("   Performance ainda está abaixo do esperado.")
    else:
        print("\n❌ FALHA TOTAL")
        print("   Nenhum teste foi bem-sucedido. Verifique se o servidor está rodando.")
    
    print(f"\n{'═'*60}\n")
    
    # Retornar código de saída
    if total_sucesso == total_testes and all(v < 5 for v in resultados.values() if v):
        sys.exit(0)  # Sucesso
    else:
        sys.exit(1)  # Falha

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
