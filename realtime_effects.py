import numpy as np
import sounddevice as sd
from scipy.signal import butter, lfilter
import time
import json
import os

class RealtimeEffects:
    def __init__(self, config_path='default_config.json'):
        """Procesa audio del sistema en tiempo real con efectos meditativos extendidos."""
        config = self.load_config(config_path)
        self.sample_rate = 44100
        self.block_size = 1024

        # Parámetros básicos
        self.volume = config.get("volume", 0.5)
        self.bitcrush = config.get("bitcrush", {"bit_depth": 8, "sample_rate_factor": 0.6})
        self.glitch_prob = config.get("glitch_prob", 0.0005)
        self.glitch_amp_min = config.get("glitch_amp_min", 0.9)  # Nuevo
        self.glitch_amp_max = config.get("glitch_amp_max", 1.1)  # Nuevo
        self.mix = config.get("mix", 1.0)

        # Filtro configurable
        self.filter_type = config.get("filter_type", "lowpass")  # lowpass, highpass, bandpass
        self.filter_order = config.get("filter_order", 2)
        self.cutoff_freq_low = config.get("cutoff_freq_low", 300)  # para lowpass o highpass
        self.cutoff_freq_high = config.get("cutoff_freq_high", 3000)  # para bandpass

        # LFO parámetros
        self.lfo_min_freq = config.get("lfo_min_freq", 0.005)
        self.lfo_max_freq = config.get("lfo_max_freq", 0.02)
        self.lfo_waveform = config.get("lfo_waveform", "sine")  # sine, triangle, square
        self.lfo_depth = config.get("lfo_depth", 0.03)

        # Stereo panning LFO
        self.pan_lfo_min_freq = config.get("pan_lfo_min_freq", 0.1)
        self.pan_lfo_max_freq = config.get("pan_lfo_max_freq", 0.3)
        self.pan_lfo_waveform = config.get("pan_lfo_waveform", "sine")
        self.pan_lfo_depth = config.get("pan_lfo_depth", 0.5)  # 0 = no modulación, 1 = modulación completa

        # Delay parámetros
        self.delay_time_sec = config.get("delay_time_sec", 0.2)
        self.delay_feedback = config.get("delay_feedback", 0.3)
        self.delay_mix = config.get("delay_mix", 0.2)

        self.lfo_state = 0
        self.pan_lfo_state = 0

        # Preparar filtro
        self.prepare_filter()

        # Buffer delay para delay simple
        self.delay_buffer = np.zeros((int(self.delay_time_sec * self.sample_rate), 2), dtype=np.float32)
        self.delay_write_pos = 0

        try:
            sd.default.latency = 'high'
            input_device = self.get_input_device()
            output_device = self.get_output_device()
            input_info = sd.query_devices(input_device)
            output_info = sd.query_devices(output_device)
            print(f"Input device: {input_info['name']}, channels: {input_info['max_input_channels']}")
            print(f"Output device: {output_info['name']}, channels: {output_info['max_output_channels']}")
            self.stream = sd.Stream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=2,
                callback=self.audio_callback,
                device=(input_device, output_device),
                latency='high'
            )
            self.stream.start()
            print("RealtimeEffects: Audio processing started")
        except Exception as e:
            print(f"RealtimeEffects: Error initializing audio: {e}")

    def prepare_filter(self):
        nyquist = 0.5 * self.sample_rate
        if self.filter_type == "lowpass":
            normal_cutoff = self.cutoff_freq_low / nyquist
            self.b, self.a = butter(self.filter_order, normal_cutoff, btype='low')
        elif self.filter_type == "highpass":
            normal_cutoff = self.cutoff_freq_low / nyquist
            self.b, self.a = butter(self.filter_order, normal_cutoff, btype='high')
        elif self.filter_type == "bandpass":
            low = self.cutoff_freq_low / nyquist
            high = self.cutoff_freq_high / nyquist
            self.b, self.a = butter(self.filter_order, [low, high], btype='band')
        else:
            # Default lowpass
            normal_cutoff = self.cutoff_freq_low / nyquist
            self.b, self.a = butter(self.filter_order, normal_cutoff, btype='low')

    def load_config(self, path):
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {}

    def get_input_device(self):
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if 'CABLE Output' in dev['name']:
                return i
        print("RealtimeEffects: CABLE Output not found, using default input.")
        return sd.default.device[0]

    def get_output_device(self):
        devices = sd.query_devices()
        h1n_keywords = ['H Series', 'Zoom']
        fallback_keywords = ['Speakers (Realtek(R) Audio)', 'Speakers', 'Realtek', 'Headphones']

        for i, dev in enumerate(devices):
            if dev['max_output_channels'] >= 2:
                if any(keyword in dev['name'] for keyword in h1n_keywords):
                    print(f"Selected output device (H1n): {dev['name']}")
                    return i

        for i, dev in enumerate(devices):
            if dev['max_output_channels'] >= 2:
                if any(keyword in dev['name'] for keyword in fallback_keywords):
                    print(f"Selected fallback output device: {dev['name']}")
                    return i

        print("RealtimeEffects: No suitable output device found, using default output.")
        return sd.default.device[1]

    def apply_bitcrush(self, audio, bit_depth=8, sample_rate_factor=0.6):
        frames, channels = audio.shape
        if sample_rate_factor < 1.0:
            new_len = int(frames * sample_rate_factor)
            new_len = max(1, new_len)
            indices = np.linspace(0, frames - 1, new_len).astype(int)
            audio = audio[indices, :]
            pad_len = frames - audio.shape[0]
            if pad_len > 0:
                audio = np.vstack([audio, np.zeros((pad_len, channels))])
        if bit_depth < 16:
            max_val = 2 ** (bit_depth - 1) - 1
            audio = np.round(audio / max_val) * max_val
        return audio.astype(np.float32)

    def lfo_wave(self, t, waveform):
        """Genera el valor del LFO según tipo de onda."""
        if waveform == "sine":
            return np.sin(2 * np.pi * t)
        elif waveform == "triangle":
            return 2 * np.abs(2 * (t % 1) - 1) - 1
        elif waveform == "square":
            return np.where((t % 1) < 0.5, 1, -1)
        else:
            return np.sin(2 * np.pi * t)  # default seno

    def audio_callback(self, indata, outdata, frames, time_info, status):
        if status:
            print(f"Audio callback status: {status}")

        if frames != self.block_size:
            outdata[:] = np.zeros((frames, 2))
            return

        dry_audio = indata[:, :2].copy()

        # Aplicar filtro configurable
        wet_audio = lfilter(self.b, self.a, dry_audio, axis=0)

        # LFO para modulación de volumen
        t = np.linspace(self.lfo_state, self.lfo_state + frames / self.sample_rate, frames)
        self.lfo_state += frames / self.sample_rate
        freq = np.random.uniform(self.lfo_min_freq, self.lfo_max_freq)
        lfo_val = self.lfo_wave(t * freq, self.lfo_waveform)
        modulation = 1 + self.lfo_depth * lfo_val
        wet_audio *= modulation[:, np.newaxis]

        # Glitch
        if np.random.rand() < 0.2:
            glitch_mask = np.random.rand(frames) < self.glitch_prob
            glitch_factors = np.random.uniform(self.glitch_amp_min, self.glitch_amp_max, glitch_mask.sum())
            wet_audio[glitch_mask] *= glitch_factors[:, np.newaxis]

        # Bitcrush
        wet_audio = (wet_audio * 32767).astype(np.float32)
        wet_audio = self.apply_bitcrush(wet_audio,
                                        self.bitcrush.get('bit_depth', 8),
                                        self.bitcrush.get('sample_rate_factor', 0.6))

        # Normalizar wet_audio
        max_val = np.max(np.abs(wet_audio))
        if max_val > 0:
            wet_audio = wet_audio / max_val * 0.9 * self.volume
        else:
            wet_audio = np.zeros_like(wet_audio)

        # LFO para modulación de panning estéreo
        t_pan = np.linspace(self.pan_lfo_state, self.pan_lfo_state + frames / self.sample_rate, frames)
        self.pan_lfo_state += frames / self.sample_rate
        pan_freq = np.random.uniform(self.pan_lfo_min_freq, self.pan_lfo_max_freq)
        pan_lfo_val = self.lfo_wave(t_pan * pan_freq, self.pan_lfo_waveform)
        pan_mod = self.pan_lfo_depth * pan_lfo_val  # rango -depth a +depth

        # Aplicar panning: pan_mod controla cuánto panea a la derecha o izquierda
        # pan_mod = -1 (todo a izq), 0 centro, +1 todo a der
        left_gain = np.clip(1 - pan_mod, 0, 1)
        right_gain = np.clip(1 + pan_mod, 0, 1)

        stereo_audio = np.zeros_like(wet_audio)
        stereo_audio[:, 0] = wet_audio[:, 0] * left_gain
        stereo_audio[:, 1] = wet_audio[:, 1] * right_gain

        # Delay simple en buffer circular
        delay_len = self.delay_buffer.shape[0]
        out = np.zeros_like(stereo_audio)
        for i in range(frames):
            delay_read_pos = (self.delay_write_pos - delay_len) % delay_len
            delayed_sample = self.delay_buffer[delay_read_pos]
            out[i] = stereo_audio[i] + delayed_sample * self.delay_feedback
            self.delay_buffer[self.delay_write_pos] = out[i]
            self.delay_write_pos = (self.delay_write_pos + 1) % delay_len

        # Mezclar dry y wet + delay según self.mix y delay_mix
        mixed_audio = (out * self.mix * (1 - self.delay_mix)) + (dry_audio * (1 - self.mix))

        # Salida
        outdata[:] = mixed_audio.astype(np.float32)

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
        print("RealtimeEffects: Stopped")

if __name__ == "__main__":
    effects = RealtimeEffects()
    try:
        print("Presiona Ctrl+C para detener...")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        effects.stop()
        print("RealtimeEffects: Playback stopped")
