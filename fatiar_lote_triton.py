import os
import json
import struct
import numpy as np
import soundfile as sf

AUDIO_FILE = "/root/lote_int_a_final.wav"
MAPA_FILE = "/root/mapa_lote_int_a.json"
OUTPUT_DIR = "/root/kits_extraidos"

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

def chunk(tag, data):
    pad = b'\x00' if len(data) % 2 != 0 else b''
    return tag.encode('ascii')[:4] + struct.pack('<I', len(data)) + data + pad

def list_chunk(list_type, subchunks):
    data = list_type.encode('ascii')[:4] + b''.join(subchunks)
    return chunk('LIST', data)

def gerar_sf2(sf2_path, kit_nome, samples_info, sample_rate=44100):
    """
    Gera um SoundFont 2.04 binario estrito com todas as 9 tabelas RIFF e sentinelas EOS.
    Totalmente compativel com Polyphone sem dar erro de arquivo corrompido.
    """
    # 1. INFO
    ifil = struct.pack('<HH', 2, 1)
    isng = b'EMU8000\x00'
    inam = kit_nome[:250].encode('ascii', errors='ignore') + b'\x00'
    if len(inam) % 2 != 0:
        inam += b'\x00'  # Garante tamanho par exigido pelo leitor de SoundFont do Polyphone
    info_list = list_chunk('INFO', [chunk('ifil', ifil), chunk('isng', isng), chunk('INAM', inam)])

    # 2. sdta (samples)
    smpl_bytes = bytearray()
    shdr_records = []
    igen_records = []
    ibag_records = []

    samples_info = sorted(samples_info, key=lambda x: x['nota'])

    for s_idx, s in enumerate(samples_info):
        audio_int16 = s['pcm_data']
        num_samples = len(audio_int16) // 2
        start_idx = len(smpl_bytes) // 2
        end_idx = start_idx + num_samples

        smpl_bytes.extend(audio_int16)
        smpl_bytes.extend(b'\x00\x00' * 46) # 46 samples silêncio exigidos pela norma SF2

        start_loop = start_idx
        end_loop = end_idx

        s_name = f"S_{s['nota']}_{s['nome'][:12]}".encode('ascii', errors='ignore')[:19].ljust(20, b'\x00')
        shdr_records.append(struct.pack('<20sIIIIIBbHH',
            s_name, start_idx, end_idx, start_loop, end_loop, sample_rate, s['nota'], 0, 0, 1
        ))

        current_igen_idx = len(igen_records)
        ibag_records.append(struct.pack('<HH', current_igen_idx, 0))
        igen_records.append(struct.pack('<HBB', 43, s['nota'], s['nota'])) # keyRange
        igen_records.append(struct.pack('<Hh', 58, s['nota']))             # overridingRootKey
        igen_records.append(struct.pack('<HH', 53, s_idx))                 # sampleID

    # Sentinelas obrigatorios
    shdr_records.append(struct.pack('<20sIIIIIBbHH', b'EOS'.ljust(20, b'\x00'), 0, 0, 0, 0, 0, 0, 0, 0, 0))
    ibag_records.append(struct.pack('<HH', len(igen_records), 0))
    igen_records.append(struct.pack('<HH', 0, 0))

    inst_name = kit_nome[:19].encode('ascii', errors='ignore').ljust(20, b'\x00')
    inst_records = [
        struct.pack('<20sH', inst_name, 0),
        struct.pack('<20sH', b'EOI'.ljust(20, b'\x00'), len(ibag_records) - 1)
    ]

    preset_name = kit_nome[:19].encode('ascii', errors='ignore').ljust(20, b'\x00')
    phdr_records = [
        struct.pack('<20sHHHIII', preset_name, 0, 128, 0, 0, 0, 0),
        struct.pack('<20sHHHIII', b'EOP'.ljust(20, b'\x00'), 255, 255, 1, 0, 0, 0)
    ]
    pbag_records = [struct.pack('<HH', 0, 0), struct.pack('<HH', 1, 0)]
    pgen_records = [struct.pack('<HH', 41, 0), struct.pack('<HH', 0, 0)]
    imod_data = struct.pack('<HHhHH', 0, 0, 0, 0, 0)
    pmod_data = struct.pack('<HHhHH', 0, 0, 0, 0, 0)

    sdta_list = list_chunk('sdta', [chunk('smpl', bytes(smpl_bytes))])
    pdta_list = list_chunk('pdta', [
        chunk('phdr', b''.join(phdr_records)),
        chunk('pbag', b''.join(pbag_records)),
        chunk('pmod', pmod_data),
        chunk('pgen', b''.join(pgen_records)),
        chunk('inst', b''.join(inst_records)),
        chunk('ibag', b''.join(ibag_records)),
        chunk('imod', imod_data),
        chunk('igen', b''.join(igen_records)),
        chunk('shdr', b''.join(shdr_records))
    ])

    full_sf2 = chunk('RIFF', b'sfbk' + info_list + sdta_list + pdta_list)
    with open(sf2_path, 'wb') as f:
        f.write(full_sf2)

def main():
    if not os.path.exists(AUDIO_FILE):
        print(f"Erro: Arquivo de audio {AUDIO_FILE} nao encontrado!")
        return
    if not os.path.exists(MAPA_FILE):
        print(f"Erro: Arquivo do mapa {MAPA_FILE} nao encontrado!")
        return

    print("Carregando mapa de fatiamento...")
    with open(MAPA_FILE, 'r') as f:
        mapa = json.load(f)

    print(f"Carregando audio renderizado: {AUDIO_FILE}...")
    audio_data, sr = sf.read(AUDIO_FILE)
    total_samples = len(audio_data)

    # Agrupa por kit
    kits = {}
    for item in mapa:
        kn = item.get("kit_nome", "Kit_Desconhecido")
        if kn not in kits:
            kits[kn] = []
        kits[kn].append(item)

    print(f"Encontrados {len(kits)} kit(s) no mapa:")
    for kn in kits:
        print(f" - {kn}: {len(kits[kn])} pecas")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for kit_nome, items in kits.items():
        print(f"\nProcessando Kit: {kit_nome}...")
        kit_dir = os.path.join(OUTPUT_DIR, kit_nome)
        samples_dir = os.path.join(kit_dir, "samples")
        os.makedirs(samples_dir, exist_ok=True)

        sf2_samples_info = []
        sfz_regions = []

        for item in items:
            nota = int(item["nota"])
            nome_gm = GM_NAMES.get(nota, f"Perc_{nota}")
            t_ini = float(item["inicio_s"])
            t_fim = float(item["fim_s"])

            idx_ini = max(0, int(t_ini * sr))
            idx_fim = min(total_samples, int(t_fim * sr))

            if idx_fim <= idx_ini:
                continue

            fatia = audio_data[idx_ini:idx_fim]

            # Normaliza e salva em WAV 16-bit
            wav_nome = f"{nota}_{nome_gm}.wav"
            wav_path = os.path.join(samples_dir, wav_nome)
            sf.write(wav_path, fatia, sr, subtype='PCM_16')

            # Prepara versao mono 16-bit para o SF2
            if len(fatia.shape) > 1:
                fatia_mono = fatia.mean(axis=1)
            else:
                fatia_mono = fatia

            # Converte float para PCM 16-bit int16
            pcm_int16 = (np.clip(fatia_mono, -1.0, 1.0) * 32767).astype(np.int16).tobytes()

            sf2_samples_info.append({
                'nota': nota,
                'nome': nome_gm,
                'pcm_data': pcm_int16
            })

            sfz_regions.append(
                f"<region>\n"
                f"sample={wav_nome}\n"
                f"key={nota}\n"
                f"pitch_keycenter={nota}\n"
                f"ampeg_release=0.1\n"
            )

        # 1. Gera arquivo SFZ
        sfz_path = os.path.join(kit_dir, f"{kit_nome}.sfz")
        with open(sfz_path, 'w', encoding='utf-8') as f_sfz:
            f_sfz.write(f"// SFZ Instrument: {kit_nome}\n")
            f_sfz.write(f"// Gerado automaticamente pelo Agent Nexora\n\n")
            f_sfz.write("<control>\ndefault_path=samples/\n\n")
            f_sfz.write("<global>\nampeg_release=0.1\n\n")
            f_sfz.write("<group>\n\n")
            for reg in sfz_regions:
                f_sfz.write(reg + "\n")

        # 2. Gera arquivo SF2 oficial
        sf2_path = os.path.join(kit_dir, f"{kit_nome}.sf2")
        gerar_sf2(sf2_path, kit_nome, sf2_samples_info, sample_rate=sr)

        print(f"✓ {kit_nome}: {len(items)} pecas fatiadas | SFZ gerado | SF2 gerado com sucesso!")

    print(f"\n==========================================")
    print(f"Sucesso! Todos os kits estao em: {OUTPUT_DIR}")
    print(f"==========================================")

if __name__ == "__main__":
    main()
