#!/usr/bin/env python3
# ==============================================================================
# gerar_sequencia_midi_triton.py — Gerador de Sequência MIDI e Mapa de Fatiamento
# ==============================================================================
import os
import json
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

# 10 Kits Clássicos do KORG Triton
KITS_TRITON = [
    "01_Standard_Kit_1",
    "02_Standard_Kit_2",
    "03_Room_Kit",
    "04_Rock_Kit",
    "05_Electronic_Kit",
    "06_Analog_Kit",
    "07_Jazz_Kit",
    "08_Brush_Kit",
    "09_Orchestra_Kit",
    "10_Dance_Kit"
]

# Notas padrão General MIDI / KORG Triton (35 a 81)
GM_NAMES = {
    35: "Bass_Drum_2", 36: "Bass_Drum_1", 37: "Side_Stick", 38: "Snare_1",
    39: "Clap", 40: "Snare_2", 41: "Low_Tom_2", 42: "Closed_HH",
    43: "Low_Tom_1", 44: "Pedal_HH", 45: "Mid_Tom_2", 46: "Open_HH",
    47: "Mid_Tom_1", 48: "High_Tom_2", 49: "Crash_1", 50: "High_Tom_1",
    51: "Ride_1", 52: "China", 53: "Ride_Bell", 54: "Tambourine",
    55: "Splash", 56: "Cowbell", 57: "Crash_2", 58: "Vibraslap",
    59: "Ride_2", 60: "Hi_Bongo", 61: "Low_Bongo", 62: "Mute_Conga",
    63: "Open_Conga", 64: "Low_Conga", 65: "Hi_Timbale", 66: "Low_Timbale",
    67: "Hi_Agogo", 68: "Low_Agogo", 69: "Cabasa", 70: "Maracas",
    71: "Short_Whistle", 72: "Long_Whistle", 73: "Short_Guiro", 74: "Long_Guiro",
    75: "Claves", 76: "Hi_Woodblock", 77: "Low_Woodblock", 78: "Mute_Cuica",
    79: "Open_Cuica", 80: "Mute_Triangle", 81: "Open_Triangle"
}

def gerar_sequencia_e_mapa(
    output_mid="/root/sequencia_10_kits_triton.mid",
    output_json="/root/mapa_lote_int_a.json",
    tempo_bpm=120,
    duracao_nota_s=0.5,
    intervalo_silencio_s=2.0
):
    """
    Gera um arquivo MIDI contendo o acionamento sequencial das notas
    de 10 kits de bateria, com tempo de cauda suficiente para pratos e reverberação.
    Gera também o mapa JSON para o fatiador cortar automaticamente.
    """
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    # Configuração de Tempo (120 BPM = 500.000 microssegundos por beat)
    tempo_us = int(60_000_000 / tempo_bpm)
    track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
    track.append(MetaMessage('track_name', name='Korg Triton 10 Kits Sampler', time=0))

    ticks_por_segundo = (mid.ticks_per_beat * tempo_bpm) / 60.0

    tempo_atual_s = 1.0  # Começa com 1s de silêncio inicial
    ticks_acumulados = int(tempo_atual_s * ticks_por_segundo)
    
    # Adiciona silêncio inicial
    track.append(Message('note_off', note=0, velocity=0, time=ticks_acumulados))

    mapa_fatiamento = []

    print(f"🎵 Gerando sequência MIDI para {len(KITS_TRITON)} kits...")

    for kit_idx, kit_nome in enumerate(KITS_TRITON):
        print(f"  -> Kit [{kit_idx+1}/10]: {kit_nome}")
        
        # Pausa de 3 segundos entre kits para permitir troca manual ou automação
        if kit_idx > 0:
            pausa_kit_s = 3.0
            ticks_pausa = int(pausa_kit_s * ticks_por_segundo)
            track.append(Message('note_off', note=0, velocity=0, time=ticks_pausa))
            tempo_atual_s += pausa_kit_s

        for nota in sorted(GM_NAMES.keys()):
            nome_peca = GM_NAMES[nota]
            inicio_s = tempo_atual_s
            fim_s = inicio_s + duracao_nota_s + intervalo_silencio_s

            mapa_fatiamento.append({
                "kit_nome": kit_nome,
                "nota": nota,
                "nome_peca": nome_peca,
                "inicio_s": round(inicio_s, 4),
                "fim_s": round(fim_s, 4),
                "duracao_s": round(fim_s - inicio_s, 4)
            })

            # Note On (Velocity 127 - Máxima dinâmica)
            track.append(Message('note_on', note=nota, velocity=127, time=0, channel=9))

            # Duração da nota ativa (Note Off)
            ticks_nota = int(duracao_nota_s * ticks_por_segundo)
            track.append(Message('note_off', note=nota, velocity=0, time=ticks_nota, channel=9))

            # Intervalo de cauda e silêncio até a próxima peça
            ticks_silencio = int(intervalo_silencio_s * ticks_por_segundo)
            track.append(Message('note_off', note=0, velocity=0, time=ticks_silencio, channel=9))

            tempo_atual_s = fim_s

    # Salva arquivos
    os.makedirs(os.path.dirname(output_mid), exist_ok=True)
    mid.save(output_mid)
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(mapa_fatiamento, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Arquivo MIDI salvo em: {output_mid}")
    print(f"✓ Mapa de Fatiamento JSON salvo em: {output_json}")
    print(f"✓ Total de amostras mapeadas: {len(mapa_fatiamento)} peças")
    print(f"✓ Duração total da renderização: {round(tempo_atual_s / 60.0, 1)} minutos")

if __name__ == "__main__":
    gerar_sequencia_e_mapa()
