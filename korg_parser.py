#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Korg PA Series Style Parser & Arranger Engine Analyzer
Suporta: Korg Pa4x, Pa3x, Pa1000, Pa700, Pa600, Pa500, Pa80, Pa50 (.STY, .SET)
Engenharia Reversa de:
- Canais MIDI (Drums, Bass, Acc1-Acc5)
- Variações (Intro, Var 1-4, Fill, Break, Ending)
- Comportamento do Baixo e Motor de Harmonização de Acordes (NTT / Chord Rules)
"""

import sys
import os
import struct
import json
from typing import Dict, List, Any, Optional

NOME_NOTAS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def midi_para_nota(num: int) -> str:
    oitava = (num // 12) - 1
    nome = NOME_NOTAS[num % 12]
    return f"{nome}{oitava}"

MAPA_CANAIS_KORG = {
    8: {"nome": "Acc 5", "tipo": "Acompanhamento"},
    9: {"nome": "Bass (Baixo)", "tipo": "Baixo Harmônico"},
    10: {"nome": "Drums (Bateria)", "tipo": "Percussão Rítmica"},
    11: {"nome": "Percussion (Percussão)", "tipo": "Percussão"},
    12: {"nome": "Acc 1", "tipo": "Acompanhamento Harmônico (Guitarras/Pianos)"},
    13: {"nome": "Acc 2", "tipo": "Acompanhamento Harmônico (Pads/Cordas)"},
    14: {"nome": "Acc 3", "tipo": "Acompanhamento Melódico/Brass"},
    15: {"nome": "Acc 4", "tipo": "Acompanhamento Melódico/Arpeggio"}
}

class KorgStyleAnalyzer:
    def __init__(self, caminho_arquivo: str):
        self.caminho = caminho_arquivo
        self.dados_raw = b""
        self.tamanho = 0
        self.tempos = []
        self.compassos = []
        self.marcadores = []
        self.tracks = []
        self.notas_baixo = []
        self.notas_por_canal = {ch: [] for ch in range(16)}
        self.info_estilo = {
            "nome_arquivo": os.path.basename(caminho_arquivo),
            "formato": "Korg PA Style (.sty)",
            "offset_midi": -1,
            "tracks_encontradas": 0,
            "bpm_estimado": 120,
            "compasso": "4/4",
            "secoes_detectadas": []
        }

    def carregar(self) -> bool:
        if not os.path.exists(self.caminho):
            print(f"[!] Arquivo não encontrado: {self.caminho}")
            return False
        with open(self.caminho, 'rb') as f:
            self.dados_raw = f.read()
        self.tamanho = len(self.dados_raw)
        print(f"[*] Arquivo carregado: {self.tamanho} bytes")
        return True

    def analisar_cabecalho_korg(self):
        """Extrai metadados do cabeçalho proprietário KORG Pa4x antes ou durante o MIDI"""
        idx_mthd = self.dados_raw.find(b'MThd')
        if idx_mthd != -1:
            self.info_estilo["offset_midi"] = idx_mthd
            print(f"[✓] Chunk MIDI MThd detectado no offset {idx_mthd}")
            if idx_mthd > 0:
                cabecalho_korg = self.dados_raw[:idx_mthd]
                # Busca strings legíveis no cabeçalho
                textos = []
                temp = []
                for b in cabecalho_korg:
                    if 32 <= b <= 126:
                        temp.append(chr(b))
                    else:
                        if len(temp) >= 3:
                            textos.append("".join(temp))
                        temp = []
                if textos:
                    self.info_estilo["metadados_cabecalho"] = textos[:10]
        else:
            print("[!] Aviso: Assinatura MThd padrão não encontrada no offset 0. Analisando blocos binários Korg...")

    def parsear_midi_stream(self):
        """Usa mido se disponível ou parser SMF nativo em fallback"""
        offset = self.info_estilo.get("offset_midi", 0)
        if offset == -1:
            offset = 0

        try:
            import mido
            import io
            midi_bytes = self.dados_raw[offset:]
            mid = mido.MidiFile(file=io.BytesIO(midi_bytes))
            self.info_estilo["tracks_encontradas"] = len(mid.tracks)
            self.info_estilo["ticks_por_beat"] = mid.ticks_per_beat

            for i, track in enumerate(mid.tracks):
                tempo_acumulado = 0
                nome_track = f"Track_{i}"
                for msg in track:
                    tempo_acumulado += msg.time
                    if msg.type == 'track_name':
                        nome_track = msg.name
                    elif msg.type == 'marker' or msg.type == 'text':
                        texto = getattr(msg, 'text', '')
                        self.marcadores.append({"tempo": tempo_acumulado, "texto": texto, "track": i})
                        if any(s in texto.lower() for s in ['var', 'intro', 'fill', 'end', 'cv', 'basic']):
                            self.info_estilo["secoes_detectadas"].append(texto)
                    elif msg.type == 'set_tempo':
                        bpm = round(mido.tempo2bpm(msg.tempo), 1)
                        self.tempos.append(bpm)
                        self.info_estilo["bpm_estimado"] = bpm
                    elif msg.type == 'time_signature':
                        comp = f"{msg.numerator}/{msg.denominator}"
                        self.compassos.append(comp)
                        self.info_estilo["compasso"] = comp
                    elif msg.type == 'note_on' and msg.velocity > 0:
                        canal = msg.channel
                        nota = msg.note
                        info_n = {
                            "tick": tempo_acumulado,
                            "canal": canal,
                            "nota_midi": nota,
                            "nota_nome": midi_para_nota(nota),
                            "velocity": msg.velocity,
                            "track_idx": i,
                            "track_nome": nome_track
                        }
                        self.notas_por_canal[canal].append(info_n)
                        # Canal 9 ou notas da track identificada como Bass
                        if canal == 9 or "bass" in nome_track.lower():
                            self.notas_baixo.append(info_n)

            print(f"[✓] Parsing MIDI concluído via Mido: {len(mid.tracks)} pistas analisadas.")
            return True
        except Exception as e:
            print(f"[*] Parsing secundário com scanner de chunks binários (motivo: {e})")
            return self._parse_binario_manual(offset)

    def _parse_binario_manual(self, offset: int) -> bool:
        """Scanner binário de eventos MIDI para arquivos protegidos ou híbridos Korg"""
        ptr = offset
        total = len(self.dados_raw)
        while ptr < total - 8:
            fourcc = self.dados_raw[ptr:ptr+4]
            if fourcc == b'MTrk':
                tam_track = struct.unpack('>I', self.dados_raw[ptr+4:ptr+8])[0]
                ptr_track = ptr + 8
                fim_track = min(ptr_track + tam_track, total)
                
                # Varre eventos simples na track
                while ptr_track < fim_track:
                    # Avança delta-time variable length
                    while ptr_track < fim_track and (self.dados_raw[ptr_track] & 0x80):
                        ptr_track += 1
                    ptr_track += 1 # último byte do delta
                    if ptr_track >= fim_track: break
                    
                    status = self.dados_raw[ptr_track]
                    if (status & 0xF0) in (0x90, 0x80) and ptr_track + 2 < fim_track:
                        canal = status & 0x0F
                        nota = self.dados_raw[ptr_track+1]
                        vel = self.dados_raw[ptr_track+2]
                        if (status & 0xF0) == 0x90 and vel > 0:
                            info_n = {
                                "tick": ptr_track,
                                "canal": canal,
                                "nota_midi": nota,
                                "nota_nome": midi_para_nota(nota),
                                "velocity": vel
                            }
                            self.notas_por_canal[canal].append(info_n)
                            if canal == 9:
                                self.notas_baixo.append(info_n)
                        ptr_track += 3
                    else:
                        ptr_track += 1
                        
                ptr = fim_track
            else:
                ptr += 1
        return True

    def extrair_logica_arranjador_korg(self) -> Dict[str, Any]:
        """Modela as regras fundamentais do motor de arranjos da Korg (NTT e Acordes)"""
        # Análise das notas de baixo
        alturas_baixo = [n["nota_midi"] for n in self.notas_baixo]
        nota_min = min(alturas_baixo) if alturas_baixo else 36 # C2
        nota_max = max(alturas_baixo) if alturas_baixo else 60 # C4
        
        # Como o motor da Korg lê o baixo:
        # A Korg grava o Bass geralmente sobre Cmaj7 ou C7 (Root = C).
        # Quando o tecladista aperta um acorde na mão esquerda (ex: Dm, G7, F),
        # o motor executa:
        # 1. ROOT TRANSPOSE: Delta = (Tônica_Acorde - Tônica_Referência) % 12
        # 2. CHORD NOTE TABLE: Terça menor em acorde menor (E vira Eb), Sétima etc.
        # 3. HIGH/LOW KEY LIMIT (Wrap-around): Se a nota transposta passar de nota_max,
        #    ela desce 12 semitons (1 oitava) para manter o baixo firme e consistente.
        
        return {
            "baixo": {
                "total_notas_detectadas": len(self.notas_baixo),
                "extensao_frequencia": {
                    "nota_mais_grave": f"{midi_para_nota(nota_min)} (MIDI {nota_min})",
                    "nota_mais_aguda": f"{midi_para_nota(nota_max)} (MIDI {nota_max})",
                    "oitavas_usadas": round((nota_max - nota_min) / 12, 1)
                },
                "canal_padrao_korg": "Canal MIDI 9 (Track Bass)",
                "regra_harmonizacao_ntt": {
                    "tipo": "Root Transposition + Chord Table Modification",
                    "graus_fundamentais": ["Tônica (Root)", "5ª Justa (Fifth)", "Oitava (Octave)", "Notas de Passagem"],
                    "comportamento_acorde_menor": "3ª maior é automaticamente transposta para 3ª menor (-1 semitom)",
                    "comportamento_acorde_com_baixo_invertido": "Slash Chords (ex: C/E ou G/B) forçam a tônica do baixo para o baixo indicado após a barra"
                }
            },
            "distribuicao_instrumentos": {
                f"Canal_{ch}": {
                    "identificacao": MAPA_CANAIS_KORG.get(ch, {}).get("nome", f"Canal {ch}"),
                    "tipo": MAPA_CANAIS_KORG.get(ch, {}).get("tipo", "Geral"),
                    "total_notas": len(self.notas_por_canal[ch])
                }
                for ch in range(16) if len(self.notas_por_canal[ch]) > 0
            },
            "secoes_estilo": list(set(self.info_estilo.get("secoes_detectadas", []))),
            "especificacao_arranjador": {
                "estrutura_korg": "Intro 1-3, Variation 1-4, Fill 1-3, Break, Ending 1-3",
                "chord_variations_cv": "CV1 a CV6 por Variação (acordes Maiores, Menores, 7ª, Diminutos)",
                "tabela_ntt_korg": "Note Trigger Table: determina se a pista segue tônica estrita ou acorde tonal",
                "wrap_around_rule": "Evita saltos bruscos no arranjo limitando notas fora da tessitura ideal"
            }
        }

    def gerar_relatorio_completo(self, pasta_saida: str) -> str:
        os.makedirs(pasta_saida, exist_ok=True)
        self.analisar_cabecalho_korg()
        self.parsear_midi_stream()
        analise = self.extrair_logica_arranjador_korg()
        
        caminho_json = os.path.join(pasta_saida, "korg_style_analysis.json")
        with open(caminho_json, 'w', encoding='utf-8') as f:
            json.dump({
                "info_arquivo": self.info_estilo,
                "analise_arranjador": analise,
                "amostra_notas_baixo": self.notas_baixo[:50]
            }, f, indent=4, ensure_ascii=False)
            
        caminho_md = os.path.join(pasta_saida, "COMO_O_MOTOR_KORG_FUNCIONA.md")
        with open(caminho_md, 'w', encoding='utf-8') as f:
            f.write(f"""# Arquitetura do Motor de Arranjos Korg (PA Series / Pa4x)
Arquivo Analisado: `{self.info_estilo['nome_arquivo']}`
BPM Estimado: {self.info_estilo.get('bpm_estimado', 120)} | Compasso: {self.info_estilo.get('compasso', '4/4')}

## 1. Mapeamento de Pistas no Estilo Korg
Teclados Korg PA utilizam 8 canais de acompanhamento automático (Tracks):
- **Canal 10 (Drums):** Bateria principal (kick, snare, hi-hat). Não sofre transposição harmônica.
- **Canal 11 (Percussion):** Congas, pandeiro, shakers. Não sofre transposição harmônica.
- **Canal 9 (Bass):** Contrabalho. Sofre transposição de tônica (Root) e segue inversões de acordes (Slash Chords).
- **Canais 12 a 15 (Acc 1 a Acc 4):** Pianos, violões/guitarras (RX Technology com dedilhados), cordas, metais.
- **Canal 8 (Acc 5):** Elementos rítmicos adicionais ou sintetizadores de apoio.

## 2. Como o Baixo se Comporta no Arranjo
- **Tonalidade Base Gravada:** Os styles da Korg são gravados na tônica **Dó (C)** (geralmente C Maj7 ou C7).
- **Transposição em Tempo Real:** Quando o tecladista toca um acorde na mão esquerda:
  1. O motor identifica a tônica (Root) e o tipo de acorde (Maior, Menor, 7ª, 9ª, Sus4, Diminuto, Aumentado).
  2. A distância cromática de transposição é somada às notas do baixo.
  3. **Tabela NTT (Note Trigger Table):** Se for acorde menor, a 3ª maior (Mi) é ajustada para Mi bemol (Eb).
  4. **Wrap Around (Janela de Oitava):** O motor impede que o baixo suba demais (virando agudo) ou desça abaixo do limite acústico do contrabaixo elétrico.

## 3. Construindo seu Próprio Teclado Arranjador
Para criar seu software de Teclado Arranjador:
1. **Reconhecedor de Acordes (Chord Recognizer):** Detecta notas pressionadas abaixo da tecla Split (ex: C3).
2. **Player de Pistas em Loop:** Reproduz os compassos da Variação atual (1 a 4) em loop contínuo no tempo (BPM).
3. **Módulo de Transposição de Notas (Harmonizer Engine):** Aplica a fórmula:
   `Nota_Final = WrapAround(Nota_Original + Delta_Tônica, Limite_Grave, Limite_Agudo)`
4. **Sintetizador / SoundFont (SF2 / SoundFonts Korg):** Reproduz cada canal com amostras reais de instrumentos.

Relatório gerado com sucesso em `{pasta_saida}`!
""")
        print(f"[✓] Relatório e especificações salvas em: {pasta_saida}")
        return caminho_md

if __name__ == "__main__":
    if len(sys.argv) > 1:
        caminho_arq = sys.argv[1]
    else:
        # Caminho padrão ou de teste
        caminho_arq = "/content/drive/MyDrive/AgentNexora/ArquivosPC/80sGolden.sty"
        
    pasta_out = "/content/drive/MyDrive/AgentNexora/KorgStyleParser"
    print(f"=== Analisador Korg PA Style Engine ===")
    analyzer = KorgStyleAnalyzer(caminho_arq)
    if analyzer.carregar():
        analyzer.gerar_relatorio_completo(pasta_out)
    else:
        print("Para analisar um arquivo, execute: python3 korg_parser.py /caminho/do/arquivo.sty")
