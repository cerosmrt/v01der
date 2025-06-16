# --- noise_controls.py ---
import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QTimer

class NoiseController:
    def __init__(self, sample_rate=44100, block_size=1024, volume=0.01, noise_type='brown',
                 bitcrush={'bit_depth': 8, 'sample_rate_factor': 0.6},
                 lfo_min_freq=0.01, lfo_max_freq=0.03, glitch_prob=0.001, cutoff_freq=300):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.volume = volume
        self.noise_type = noise_type
        self.bitcrush = bitcrush
        self.lfo_min_freq = lfo_min_freq
        self.lfo_max_freq = lfo_max_freq
        self.glitch_prob = glitch_prob
        self.cutoff_freq = cutoff_freq
        self.stream = None
        self.timer = None
        self.lfo_state = 0

        try:
            self.stream = sd.OutputStream(
                samplerate=sample_rate,
                blocksize=block_size,
                channels=2,
                callback=self.audio_callback
            )
            self.stream.start()
            self.start_lfo_generator()
            print(f"NoiseController: {self.noise_type.capitalize()} subtle meditative noise started.")
        except Exception as e:
            print(f"NoiseController: Error initializing audio: {str(e)}")

    def lowpass_filter(self, data, cutoff, alpha=0.1):
        """
        Filtro pasa bajos simple usando un filtro de media móvil exponencial.
        `alpha` controla la suavidad (más bajo = más suave).
        """
        filtered = np.zeros_like(data)
        filtered[0] = data[0]
        for i in range(1, len(data)):
            filtered[i] = alpha * data[i] + (1 - alpha) * filtered[i - 1]
        return filtered

    def apply_bitcrush(self, noise, bit_depth=16, sample_rate_factor=1.0):
        original_length = len(noise)
        if sample_rate_factor < 1.0:
            new_length = int(original_length * sample_rate_factor)
            new_length = max(1, new_length)
            indices = np.linspace(0, original_length - 1, new_length).astype(int)
            noise = noise[indices]
            noise = np.tile(noise, (original_length // len(noise) + 1))[:original_length]
        if bit_depth < 16:
            max_val = 2 ** (bit_depth - 1) - 1
            noise = np.round(noise / 32767 * max_val) / max_val * 32767
        return noise.astype(np.int16)

    def generate_variable_lfo(self, t, min_freq, max_freq):
        n_points = 4
        rand_freqs = np.random.uniform(min_freq, max_freq, n_points)
        rand_phases = np.random.uniform(0, 2 * np.pi, n_points)
        key_times = np.linspace(0, self.block_size / self.sample_rate, n_points)
        freqs = np.interp(t, key_times, rand_freqs)
        phases = np.interp(t, key_times, rand_phases)
        return 0.97 + 0.03 * np.sin(2 * np.pi * freqs * t + phases)

    def audio_callback(self, outdata, frames, time, status):
        if status:
            print(f"Audio callback status: {status}")
        if frames != self.block_size:
            return

        if self.noise_type == 'brown':
            white = np.random.uniform(-1, 1, frames)
            brown = np.cumsum(white)
            noise = brown / np.max(np.abs(brown)) * 0.8
        elif self.noise_type == 'white':
            noise = np.random.uniform(-1, 1, frames)
        elif self.noise_type == 'pink':
            white = np.random.uniform(-1, 1, frames)
            pink = np.cumsum(white) / np.arange(1, frames + 1) ** 0.5
            noise = pink / np.max(np.abs(pink)) * 0.8
        else:
            noise = np.zeros(frames)

        noise = self.lowpass_filter(noise, cutoff=self.cutoff_freq)

        t = np.linspace(self.lfo_state, self.lfo_state + frames / self.sample_rate, frames)
        self.lfo_state += frames / self.sample_rate
        noise *= self.generate_variable_lfo(t, self.lfo_min_freq, self.lfo_max_freq)

        if np.random.rand() < 0.25:  # reducir cantidad de glitches
            glitch_mask = np.random.random(frames) < self.glitch_prob
            noise[glitch_mask] *= np.random.uniform(0.9, 1.1, glitch_mask.sum())

        if self.bitcrush:
            bit_depth = self.bitcrush.get('bit_depth', 8)
            sample_rate_factor = self.bitcrush.get('sample_rate_factor', 0.6)
            noise = (noise * 32767).astype(np.float32)
            noise = self.apply_bitcrush(noise, bit_depth, sample_rate_factor)

        noise = noise / np.max(np.abs(noise)) * 0.1 * self.volume
        stereo_noise = np.repeat(noise[:, np.newaxis], 2, axis=1)
        outdata[:] = stereo_noise

    def start_lfo_generator(self):
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: None)
        self.timer.start(100)

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
        if self.timer:
            self.timer.stop()
        print("NoiseController: Stopped")

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        print(f"NoiseController: Volume set to {self.volume:.2f}")

    def set_noise_type(self, noise_type):
        self.noise_type = noise_type
        print(f"NoiseController: Noise type set to {self.noise_type}")

    def set_bitcrush(self, bitcrush):
        self.bitcrush = bitcrush
        print(f"NoiseController: Bitcrush set to {self.bitcrush}")

    def set_lfo_freq(self, min_freq, max_freq):
        self.lfo_min_freq = min_freq
        self.lfo_max_freq = max_freq
        print(f"NoiseController: LFO freq range set to {min_freq:.2f}-{max_freq:.2f} Hz")

    def set_glitch_prob(self, prob):
        self.glitch_prob = max(0.0, min(0.1, prob))
        print(f"NoiseController: Glitch probability set to {self.glitch_prob:.4f}")

    def set_cutoff_freq(self, cutoff):
        self.cutoff_freq = max(50, min(8000, cutoff))
        print(f"NoiseController: Cutoff frequency set to {self.cutoff_freq} Hz")
